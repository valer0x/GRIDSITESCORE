"""PDF report generation — verifies bytes, magic header, and non-trivial size."""

from app.models.schemas import (
    AnalysisResponse,
    DigitalSection,
    EnergySection,
    GridAccess,
    LatLng,
    ResilienceSection,
)
from app.services.report import render_report_pdf
from app.services.scoring import compute_score, load_config


def _make_analysis(scoring_config_path: str) -> AnalysisResponse:
    grid = GridAccess(
        nearest_hv_line_km=3.2,
        substations_10km=3,
        substations_50km=7,
        line_density_per_km2=0.09,
    )
    energy = EnergySection(
        plants_50km=12,
        total_capacity_mw_50km=2450.0,
        mix_pct={"gas": 40, "solar": 30, "hydro": 20, "wind": 10},
        renewable_share=0.60,
        fuel_diversity_shannon=1.28,
    )
    digital = DigitalSection(
        data_centers_50km=4, dc_count_100km=7, nearest_dc_km=5.4
    )
    resilience = ResilienceSection(
        nearby_nodes=18,
        avg_degree=2.6,
        nearest_substation_degree=3,
        articulation_points_20km=0,
        single_point_of_failure_risk="low",
    )
    score = compute_score(
        load_config(scoring_config_path), grid, energy, digital, resilience
    )
    return AnalysisResponse(
        location=LatLng(lat=45.4642, lng=9.1900),
        grid_access=grid,
        energy=energy,
        digital=digital,
        resilience=resilience,
        score=score,
        cache_hit=False,
        duration_ms=42.0,
    )


def test_render_report_returns_pdf_bytes(scoring_config_path):
    analysis = _make_analysis(scoring_config_path)
    pdf = render_report_pdf(analysis)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-"), "must have PDF magic header"
    assert len(pdf) > 2000, "PDF suspiciously small"


def test_render_report_handles_nulls(scoring_config_path):
    """Worst-case inputs — no plants, no DCs, no HV line — must still render."""
    grid = GridAccess(
        nearest_hv_line_km=None,
        substations_10km=0,
        substations_50km=0,
        line_density_per_km2=0.0,
    )
    energy = EnergySection(
        plants_50km=0,
        total_capacity_mw_50km=0.0,
        mix_pct={},
        renewable_share=0.0,
        fuel_diversity_shannon=0.0,
    )
    digital = DigitalSection(
        data_centers_50km=0, dc_count_100km=0, nearest_dc_km=None
    )
    resilience = ResilienceSection(
        nearby_nodes=0,
        avg_degree=0.0,
        nearest_substation_degree=0,
        articulation_points_20km=0,
        single_point_of_failure_risk="high",
    )
    score = compute_score(
        load_config(scoring_config_path), grid, energy, digital, resilience
    )
    analysis = AnalysisResponse(
        location=LatLng(lat=0.0, lng=0.0),
        grid_access=grid,
        energy=energy,
        digital=digital,
        resilience=resilience,
        score=score,
    )
    pdf = render_report_pdf(analysis)
    assert pdf.startswith(b"%PDF-")
