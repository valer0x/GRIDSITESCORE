export interface LatLng {
  lat: number;
  lng: number;
}

export interface GridAccess {
  nearest_hv_line_km: number | null;
  substations_10km: number;
  substations_50km: number;
  line_density_per_km2: number;
}

export interface EnergySection {
  plants_50km: number;
  total_capacity_mw_50km: number;
  mix_pct: Record<string, number>;
  renewable_share: number;
  fuel_diversity_shannon: number;
}

export interface DigitalSection {
  data_centers_50km: number;
  dc_count_100km: number;
  nearest_dc_km: number | null;
  fiber_landing_km: number | null;
}

export type RiskLevel = "low" | "medium" | "high";

export interface ResilienceSection {
  nearby_nodes: number;
  avg_degree: number;
  nearest_substation_degree: number;
  articulation_points_20km: number;
  single_point_of_failure_risk: RiskLevel;
}

export interface RuleBreakdown {
  name: string;
  label: string;
  metric: string;
  raw_value: number | null;
  unit: string;
  weight: number;
  normalized_score: number;
  weighted_contribution: number;
  reason: string;
}

export interface CategoryBreakdown {
  name: string;
  weight: number;
  score_0_100: number;
  weighted_contribution: number;
  rules: RuleBreakdown[];
}

export interface Score {
  total: number;
  breakdown: CategoryBreakdown[];
  weights: Record<string, number>;
  version: string;
  reasoning: string[];
}

export interface AnalysisResponse {
  location: LatLng;
  grid_access: GridAccess;
  energy: EnergySection;
  digital: DigitalSection;
  resilience: ResilienceSection;
  score: Score;
  cache_hit: boolean;
  duration_ms: number | null;
}
