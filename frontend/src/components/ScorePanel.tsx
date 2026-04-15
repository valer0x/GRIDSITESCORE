import type { AnalysisResponse } from "../api/types";
import { pdfReportUrl } from "../api/analyze";
import CategoryBreakdown from "./CategoryBreakdown";

interface Props {
  data: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
}

function totalColor(score: number): string {
  if (score >= 75) return "#16a34a";
  if (score >= 50) return "#ca8a04";
  if (score >= 25) return "#ea580c";
  return "#dc2626";
}

function MetricRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value ?? "—"}</span>
    </div>
  );
}

export default function ScorePanel({ data, loading, error }: Props) {
  if (loading) return <div className="panel-state">Analyzing location…</div>;
  if (error) return <div className="panel-state error">Error: {error}</div>;
  if (!data) {
    return (
      <div className="panel-state hint">
        Click anywhere on the map to analyze a site.
      </div>
    );
  }

  const { score, grid_access, energy, digital, resilience, location } = data;
  const color = totalColor(score.total);

  return (
    <div className="panel-content">
      <header className="panel-header">
        <h2>Site Analysis</h2>
        <div className="coord">
          {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
        </div>
      </header>

      <section className="total-score" style={{ borderColor: color }}>
        <div className="total-number" style={{ color }}>
          {score.total}
        </div>
        <div className="total-label">overall site score / 100</div>
        <div className="total-meta">
          rubric v{score.version} · {data.cache_hit ? "cached" : "fresh"}
          {data.duration_ms != null && ` · ${data.duration_ms.toFixed(0)} ms`}
        </div>
        <a
          className="report-btn"
          href={pdfReportUrl(location.lat, location.lng)}
          target="_blank"
          rel="noreferrer"
        >
          Download PDF report
        </a>
      </section>

      <section className="reasoning">
        <h3>Key drivers</h3>
        <ul>
          {score.reasoning.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </section>

      <section className="breakdown">
        <h3>Category breakdown</h3>
        {score.breakdown.map((c) => (
          <CategoryBreakdown key={c.name} category={c} />
        ))}
      </section>

      <section className="raw">
        <h3>Raw indicators</h3>
        <div className="raw-grid">
          <div>
            <h4>Grid</h4>
            <MetricRow
              label="Nearest HV line (km)"
              value={grid_access.nearest_hv_line_km?.toFixed(2) ?? null}
            />
            <MetricRow label="Substations ≤10 km" value={grid_access.substations_10km} />
            <MetricRow label="Substations ≤50 km" value={grid_access.substations_50km} />
            <MetricRow
              label="Line density (km/km²)"
              value={grid_access.line_density_per_km2.toFixed(4)}
            />
          </div>
          <div>
            <h4>Energy</h4>
            <MetricRow label="Plants ≤50 km" value={energy.plants_50km} />
            <MetricRow
              label="Capacity (MW)"
              value={energy.total_capacity_mw_50km.toFixed(1)}
            />
            <MetricRow
              label="Renewable share"
              value={`${(energy.renewable_share * 100).toFixed(1)}%`}
            />
            <MetricRow
              label="Diversity (Shannon)"
              value={energy.fuel_diversity_shannon.toFixed(2)}
            />
          </div>
          <div>
            <h4>Digital</h4>
            <MetricRow label="Data centers ≤50 km" value={digital.data_centers_50km} />
            <MetricRow label="Data centers ≤100 km" value={digital.dc_count_100km} />
            <MetricRow
              label="Nearest DC (km)"
              value={digital.nearest_dc_km?.toFixed(2) ?? null}
            />
          </div>
          <div>
            <h4>Resilience</h4>
            <MetricRow label="Nearby substations" value={resilience.nearby_nodes} />
            <MetricRow label="Avg degree" value={resilience.avg_degree.toFixed(2)} />
            <MetricRow
              label="Nearest sub. degree"
              value={resilience.nearest_substation_degree}
            />
            <MetricRow
              label="Articulation pts ≤20 km"
              value={resilience.articulation_points_20km}
            />
            <MetricRow
              label="SPOF risk"
              value={resilience.single_point_of_failure_risk}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
