"""Unit tests for the scoring engine.

Focus: normalization boundaries, weighting correctness, explainability,
and configurability (overriding thresholds changes the score).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.models.schemas import (
    DigitalSection,
    EnergySection,
    GridAccess,
    ResilienceSection,
)
from app.services.scoring import (
    ScoringConfig,
    _normalize,
    compute_score,
    load_config,
)


def _grid(**kw) -> GridAccess:
    base = dict(
        nearest_hv_line_km=5.0,
        substations_10km=2,
        substations_50km=5,
        line_density_per_km2=0.05,
    )
    base.update(kw)
    return GridAccess(**base)


def _energy(**kw) -> EnergySection:
    base = dict(
        plants_50km=4,
        total_capacity_mw_50km=1000.0,
        mix_pct={"gas": 30, "solar": 30, "wind": 20, "hydro": 20},
        renewable_share=0.30,
        fuel_diversity_shannon=1.3,
    )
    base.update(kw)
    return EnergySection(**base)


def _digital(**kw) -> DigitalSection:
    base = dict(
        data_centers_50km=2,
        dc_count_100km=3,
        nearest_dc_km=20.0,
    )
    base.update(kw)
    return DigitalSection(**base)


def _resilience(**kw) -> ResilienceSection:
    base = dict(
        nearby_nodes=10,
        avg_degree=2.5,
        nearest_substation_degree=3,
        articulation_points_20km=0,
        single_point_of_failure_risk="low",
    )
    base.update(kw)
    return ResilienceSection(**base)


# ---------- Normalization ----------


def test_normalize_linear_at_best():
    from app.services.scoring import RuleSpec

    r = RuleSpec("x", "m", 1.0, "linear", worst=0, best=10, unit="", label="x")
    assert _normalize(r, 10) == 1.0
    assert _normalize(r, 20) == 1.0  # clamped
    assert _normalize(r, 0) == 0.0
    assert _normalize(r, -5) == 0.0  # clamped
    assert _normalize(r, 5) == pytest.approx(0.5)


def test_normalize_inverse_linear():
    from app.services.scoring import RuleSpec

    r = RuleSpec(
        "x", "m", 1.0, "inverse_linear", worst=50, best=5, unit="", label="x"
    )
    assert _normalize(r, 5) == 1.0
    assert _normalize(r, 50) == 0.0
    assert _normalize(r, 27.5) == pytest.approx(0.5, abs=1e-3)
    assert _normalize(r, 1) == 1.0  # clamped
    assert _normalize(r, 500) == 0.0  # clamped


def test_normalize_none_is_zero():
    from app.services.scoring import RuleSpec

    r = RuleSpec("x", "m", 1.0, "linear", worst=0, best=10, unit="", label="x")
    assert _normalize(r, None) == 0.0


# ---------- Weighted aggregation ----------


def test_best_case_scores_100(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg,
        _grid(
            nearest_hv_line_km=1.0,
            substations_10km=5,
            substations_50km=10,
            line_density_per_km2=0.10,
        ),
        _energy(
            total_capacity_mw_50km=2000.0,
            fuel_diversity_shannon=1.5,
            renewable_share=0.50,
        ),
        _digital(nearest_dc_km=2.0, dc_count_100km=10, data_centers_50km=5),
        _resilience(
            avg_degree=3.0, nearest_substation_degree=4, articulation_points_20km=0
        ),
    )
    assert score.total == 100


def test_worst_case_scores_0(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg,
        _grid(
            nearest_hv_line_km=200.0,
            substations_10km=0,
            substations_50km=0,
            line_density_per_km2=0.0,
        ),
        _energy(
            plants_50km=0,
            total_capacity_mw_50km=0.0,
            mix_pct={},
            renewable_share=0.0,
            fuel_diversity_shannon=0.0,
        ),
        _digital(
            nearest_dc_km=500.0, dc_count_100km=0, data_centers_50km=0
        ),
        _resilience(
            nearby_nodes=0,
            avg_degree=0.0,
            nearest_substation_degree=0,
            articulation_points_20km=5,
            single_point_of_failure_risk="high",
        ),
    )
    assert score.total == 0


def test_score_is_between_0_and_100(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg, _grid(), _energy(), _digital(), _resilience()
    )
    assert 0 <= score.total <= 100


def test_score_weights_sum_to_one(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg, _grid(), _energy(), _digital(), _resilience()
    )
    assert sum(score.weights.values()) == pytest.approx(1.0, abs=1e-6)


# ---------- Explainability ----------


def test_breakdown_contains_every_rule(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg, _grid(), _energy(), _digital(), _resilience()
    )
    total_rules = sum(len(cat.rules) for cat in score.breakdown)
    expected_rules = sum(len(rules) for rules in cfg.rules.values())
    assert total_rules == expected_rules


def test_every_rule_has_reason_string(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg, _grid(), _energy(), _digital(), _resilience()
    )
    for cat in score.breakdown:
        for rule in cat.rules:
            assert rule.reason
            assert "→" in rule.reason  # formatted arrow
            assert 0.0 <= rule.normalized_score <= 1.0


def test_top_reasoning_has_entries(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(
        cfg, _grid(), _energy(), _digital(), _resilience()
    )
    assert 1 <= len(score.reasoning) <= 5
    # Every headline reason starts with a "[category]" tag
    for line in score.reasoning:
        assert line.startswith("[")


# ---------- Configurability ----------


def test_yaml_override_changes_score(tmp_path, scoring_config_path):
    """Prove the scoring rubric is driven by YAML, not hardcoded."""
    original_yaml = yaml.safe_load(Path(scoring_config_path).read_text())
    # Double the weight of the digital category; halve resilience.
    original_yaml["category_weights"]["digital"] = 0.60
    original_yaml["category_weights"]["resilience"] = 0.00
    override_path = tmp_path / "override.yaml"
    override_path.write_text(yaml.safe_dump(original_yaml))

    baseline_cfg = ScoringConfig.from_yaml(scoring_config_path)
    override_cfg = ScoringConfig.from_yaml(override_path)

    # Bad digital, good resilience => overridden score lower than baseline
    g, e, r = _grid(), _energy(), _resilience()
    bad_digital = _digital(nearest_dc_km=500.0, dc_count_100km=0, data_centers_50km=0)

    baseline = compute_score(baseline_cfg, g, e, bad_digital, r).total
    overridden = compute_score(override_cfg, g, e, bad_digital, r).total
    assert overridden < baseline


def test_version_propagates_to_output(scoring_config_path):
    cfg = load_config(scoring_config_path)
    score = compute_score(cfg, _grid(), _energy(), _digital(), _resilience())
    assert score.version == cfg.version
