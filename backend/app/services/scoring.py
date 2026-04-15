"""Configurable, explainable scoring engine.

Design:
- Rules are loaded from YAML (`scoring_config.yaml`). Each rule declares
  the metric it consumes, a piecewise-linear mapping to a [0,1]
  sub-score, and a weight within its category.
- A rule produces a `RuleBreakdown` that includes the raw value, the
  normalized score, the weighted contribution, and a human-readable
  reason. Nothing is hidden.
- Category scores are the weighted mean of their rule scores, scaled to
  0-100. The total is the weighted sum of category scores using
  `category_weights`.
- Adding a new rule = one YAML entry + populating the metric in
  `_collect_metrics`. No scoring code changes required.

This isolates policy (YAML) from mechanism (Python), which is the whole
point of "configurable".
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

from app.models.schemas import (
    CategoryBreakdown,
    DigitalSection,
    EnergySection,
    GridAccess,
    ResilienceSection,
    RuleBreakdown,
    Score,
)

RuleType = Literal["linear", "inverse_linear"]


@dataclass(frozen=True, slots=True)
class RuleSpec:
    name: str
    metric: str
    weight: float
    type: RuleType
    worst: float
    best: float
    unit: str
    label: str


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    version: str
    category_weights: dict[str, float]
    rules: dict[str, list[RuleSpec]]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ScoringConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        cats = {k: float(v) for k, v in data["category_weights"].items()}
        rules: dict[str, list[RuleSpec]] = {}
        for cat, rule_list in data["rules"].items():
            rules[cat] = [
                RuleSpec(
                    name=r["name"],
                    metric=r["metric"],
                    weight=float(r["weight"]),
                    type=r["type"],
                    worst=float(r["worst"]),
                    best=float(r["best"]),
                    unit=r.get("unit", ""),
                    label=r.get("label", r["name"]),
                )
                for r in rule_list
            ]
        # Validate weights sum to ~1 per category; don't fail hard, but
        # we renormalize defensively at scoring time.
        return cls(
            version=str(data.get("version", "0.0.0")),
            category_weights=cats,
            rules=rules,
        )


@lru_cache(maxsize=4)
def load_config(path: str) -> ScoringConfig:
    return ScoringConfig.from_yaml(path)


# ---------- Normalization primitives ----------


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _normalize(rule: RuleSpec, value: float | int | None) -> float:
    """Piecewise-linear mapping from raw value to [0,1]."""
    if value is None:
        return 0.0
    v = float(value)
    lo, hi = rule.worst, rule.best
    if rule.type == "linear":
        if hi == lo:
            return 1.0 if v >= hi else 0.0
        return _clamp01((v - lo) / (hi - lo))
    # inverse_linear: best is the low end, worst the high end
    if hi == lo:
        return 1.0 if v <= hi else 0.0
    return _clamp01((lo - v) / (lo - hi))


def _format_value(v: float | int | None, unit: str) -> str:
    if v is None:
        return "no data"
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer()):
        return f"{int(v)} {unit}".strip()
    return f"{v:.2f} {unit}".strip()


def _reason(rule: RuleSpec, raw: float | int | None, normalized: float) -> str:
    tgt = (
        f"target ≤ {rule.best:g} {rule.unit}"
        if rule.type == "inverse_linear"
        else f"target ≥ {rule.best:g} {rule.unit}"
    ).strip()
    if raw is None:
        return f"{rule.label}: no data → 0.00/1.00"
    return (
        f"{rule.label}: {_format_value(raw, rule.unit)} "
        f"({tgt}) → {normalized:.2f}/1.00"
    )


# ---------- Metric collection ----------


def _collect_metrics(
    grid: GridAccess,
    energy: EnergySection,
    digital: DigitalSection,
    resilience: ResilienceSection,
) -> dict[str, float | int | None]:
    """Flatten analysis sections into the flat namespace referenced by
    YAML rule `metric:` fields. Adding a new rule usually means adding
    one entry here."""
    return {
        # grid
        "nearest_hv_line_km": grid.nearest_hv_line_km,
        "substations_10km": grid.substations_10km,
        "substations_50km": grid.substations_50km,
        "line_density_per_km2": grid.line_density_per_km2,
        # energy
        "plants_50km": energy.plants_50km,
        "total_capacity_mw_50km": energy.total_capacity_mw_50km,
        "renewable_share": energy.renewable_share,
        "fuel_diversity_shannon": energy.fuel_diversity_shannon,
        # digital
        "data_centers_50km": digital.data_centers_50km,
        "dc_count_100km": digital.dc_count_100km,
        "nearest_dc_km": digital.nearest_dc_km,
        # resilience
        "nearby_nodes": resilience.nearby_nodes,
        "avg_degree": resilience.avg_degree,
        "nearest_substation_degree": resilience.nearest_substation_degree,
        "articulation_points_20km": resilience.articulation_points_20km,
    }


# ---------- Scoring ----------


def _score_category(
    category: str,
    category_weight: float,
    rules: list[RuleSpec],
    metrics: dict[str, Any],
) -> CategoryBreakdown:
    total_rule_weight = sum(r.weight for r in rules) or 1.0
    breakdowns: list[RuleBreakdown] = []
    weighted_sum = 0.0

    for rule in rules:
        raw = metrics.get(rule.metric)
        normalized = _normalize(rule, raw)
        share = rule.weight / total_rule_weight
        weighted_sum += normalized * share
        breakdowns.append(
            RuleBreakdown(
                name=rule.name,
                label=rule.label,
                metric=rule.metric,
                raw_value=raw,
                unit=rule.unit,
                weight=round(share, 4),
                normalized_score=round(normalized, 4),
                weighted_contribution=round(normalized * share, 4),
                reason=_reason(rule, raw, normalized),
            )
        )

    category_score_01 = _clamp01(weighted_sum)
    return CategoryBreakdown(
        name=category,
        weight=round(category_weight, 4),
        score_0_100=round(category_score_01 * 100.0, 2),
        weighted_contribution=round(category_score_01 * category_weight * 100.0, 2),
        rules=breakdowns,
    )


def _top_reasoning(breakdowns: list[CategoryBreakdown], k: int = 4) -> list[str]:
    """Return the `k` most decisive rule reasons — the rules whose
    weighted contribution is farthest from the neutral midpoint. Gives
    the user the headline 'why this score'."""
    flat: list[tuple[float, str, str]] = []
    for cat in breakdowns:
        for rule in cat.rules:
            # Distance from the mid of possible weighted contribution:
            # max contribution per rule is `rule.weight` (the within-cat share).
            mid = rule.weight / 2.0
            decisiveness = abs(rule.weighted_contribution - mid)
            flat.append((decisiveness, cat.name, rule.reason))
    flat.sort(key=lambda t: t[0], reverse=True)
    return [f"[{cat}] {reason}" for _, cat, reason in flat[:k]]


def compute_score(
    config: ScoringConfig,
    grid: GridAccess,
    energy: EnergySection,
    digital: DigitalSection,
    resilience: ResilienceSection,
) -> Score:
    metrics = _collect_metrics(grid, energy, digital, resilience)

    # Defensive: normalize category weights to sum to 1.
    cw_sum = sum(config.category_weights.values()) or 1.0
    cat_weights_norm = {
        k: v / cw_sum for k, v in config.category_weights.items()
    }

    breakdowns: list[CategoryBreakdown] = []
    total = 0.0
    for cat, rules in config.rules.items():
        w = cat_weights_norm.get(cat, 0.0)
        cb = _score_category(cat, w, rules, metrics)
        breakdowns.append(cb)
        total += (cb.score_0_100 / 100.0) * w

    total_int = int(round(total * 100))
    return Score(
        total=max(0, min(100, total_int)),
        breakdown=breakdowns,
        weights={k: round(v, 4) for k, v in cat_weights_norm.items()},
        version=config.version,
        reasoning=_top_reasoning(breakdowns),
    )
