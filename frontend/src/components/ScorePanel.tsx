import type { ReactNode } from "react";
import type { AnalysisResponse } from "../api/types";
import { pdfReportUrl } from "../api/analyze";
import CategoryBreakdown from "./CategoryBreakdown";
import ScoreRing from "./ScoreRing";
import { IconDownload, IconInfo, IconPin, IconSparkles } from "./Icons";

interface Props {
  data: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
}

function MetricRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value ?? "—"}</span>
    </div>
  );
}

function RiskPill({ risk }: { risk: "low" | "medium" | "high" }) {
  return <span className={`risk-pill risk-${risk}`}>{risk}</span>;
}

export default function ScorePanel({ data, loading, error }: Props) {
  if (loading) {
    return (
      <div className="panel-state">
        <div className="spinner" />
        <span>Analyzing location…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel-state error">
        <IconInfo size={18} />
        <div>
          <div className="panel-state-title">Analysis failed</div>
          <div className="panel-state-body">{error}</div>
        </div>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="panel-state hint">
        <IconPin size={28} />
        <div className="panel-state-title">Pick a site</div>
        <div className="panel-state-body">
          Click anywhere on the map to run a due-diligence analysis.
        </div>
      </div>
    );
  }

  const { score, grid_access, energy, digital, resilience, location } = data;

  return (
    <div className="panel-content">
      <header className="panel-header">
        <div className="panel-header-tag">
          <IconPin size={14} />
          <span>Site</span>
        </div>
        <h2>Analysis result</h2>
        <div className="coord">
          {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
        </div>
      </header>

      <div className="hero-card">
        <ScoreRing
          value={score.total}
          label="overall score"
          sublabel={`rubric v${score.version}`}
        />
        <div className="hero-meta">
          <div className="hero-meta-row">
            <span className="hero-meta-label">Status</span>
            <span className="chip">{data.cache_hit ? "cached" : "fresh"}</span>
          </div>
          {data.duration_ms != null && (
            <div className="hero-meta-row">
              <span className="hero-meta-label">Compute</span>
              <span className="chip mono">{data.duration_ms.toFixed(0)} ms</span>
            </div>
          )}
          <a
            className="report-btn"
            href={pdfReportUrl(location.lat, location.lng)}
            target="_blank"
            rel="noreferrer"
          >
            <IconDownload size={14} />
            <span>PDF report</span>
          </a>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <IconSparkles size={14} />
          <h3>Key drivers</h3>
        </div>
        <ul className="drivers">
          {score.reasoning.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </section>

      <section className="section">
        <div className="section-head">
          <h3>Category breakdown</h3>
        </div>
        {score.breakdown.map((c) => (
          <CategoryBreakdown key={c.name} category={c} />
        ))}
      </section>

      <section className="section">
        <div className="section-head">
          <h3>Raw indicators</h3>
        </div>
        <div className="raw-grid">
          <div className="raw-card">
            <div className="raw-card-title">Grid</div>
            <MetricRow
              label="Nearest HV line"
              value={
                grid_access.nearest_hv_line_km != null
                  ? `${grid_access.nearest_hv_line_km.toFixed(2)} km`
                  : null
              }
            />
            <MetricRow label="Substations ≤10 km" value={grid_access.substations_10km} />
            <MetricRow label="Substations ≤50 km" value={grid_access.substations_50km} />
            <MetricRow
              label="Line density"
              value={`${grid_access.line_density_per_km2.toFixed(4)} km/km²`}
            />
          </div>
          <div className="raw-card">
            <div className="raw-card-title">Energy</div>
            <MetricRow label="Plants ≤50 km" value={energy.plants_50km} />
            <MetricRow
              label="Capacity"
              value={`${energy.total_capacity_mw_50km.toFixed(0)} MW`}
            />
            <MetricRow
              label="Renewable"
              value={`${(energy.renewable_share * 100).toFixed(1)}%`}
            />
            <MetricRow
              label="Diversity (H)"
              value={energy.fuel_diversity_shannon.toFixed(2)}
            />
          </div>
          <div className="raw-card">
            <div className="raw-card-title">Digital</div>
            <MetricRow label="DCs ≤50 km" value={digital.data_centers_50km} />
            <MetricRow label="DCs ≤100 km" value={digital.dc_count_100km} />
            <MetricRow
              label="Nearest DC"
              value={
                digital.nearest_dc_km != null
                  ? `${digital.nearest_dc_km.toFixed(1)} km`
                  : null
              }
            />
          </div>
          <div className="raw-card">
            <div className="raw-card-title">Resilience</div>
            <MetricRow label="Graph nodes" value={resilience.nearby_nodes} />
            <MetricRow label="Avg degree" value={resilience.avg_degree.toFixed(2)} />
            <MetricRow
              label="Nearest sub deg"
              value={resilience.nearest_substation_degree}
            />
            <MetricRow
              label="SPOF risk"
              value={<RiskPill risk={resilience.single_point_of_failure_risk} />}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
