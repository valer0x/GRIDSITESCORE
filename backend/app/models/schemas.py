from typing import Literal

from pydantic import BaseModel, Field


class LatLng(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class GridAccess(BaseModel):
    nearest_hv_line_km: float | None
    substations_10km: int
    substations_50km: int
    line_density_per_km2: float


class EnergySection(BaseModel):
    plants_50km: int
    total_capacity_mw_50km: float
    mix_pct: dict[str, float]
    renewable_share: float
    fuel_diversity_shannon: float


class DigitalSection(BaseModel):
    data_centers_50km: int
    dc_count_100km: int
    nearest_dc_km: float | None
    fiber_landing_km: float | None = None


RiskLevel = Literal["low", "medium", "high"]


class ResilienceSection(BaseModel):
    nearby_nodes: int
    avg_degree: float
    nearest_substation_degree: int
    articulation_points_20km: int
    single_point_of_failure_risk: RiskLevel


class RuleBreakdown(BaseModel):
    name: str
    label: str
    metric: str
    raw_value: float | int | None
    unit: str
    weight: float
    normalized_score: float  # 0.0..1.0
    weighted_contribution: float  # 0..1 * category_weight
    reason: str


class CategoryBreakdown(BaseModel):
    name: str
    weight: float
    score_0_100: float
    weighted_contribution: float  # 0..100 share of the total
    rules: list[RuleBreakdown]


class Score(BaseModel):
    total: int  # 0..100, rounded
    breakdown: list[CategoryBreakdown]
    weights: dict[str, float]
    version: str
    reasoning: list[str]


class AnalysisResponse(BaseModel):
    location: LatLng
    grid_access: GridAccess
    energy: EnergySection
    digital: DigitalSection
    resilience: ResilienceSection
    score: Score
    cache_hit: bool = False
    duration_ms: float | None = None


class BatchRequest(BaseModel):
    points: list[LatLng] = Field(..., max_length=100)


class BatchResponse(BaseModel):
    results: list[AnalysisResponse]
