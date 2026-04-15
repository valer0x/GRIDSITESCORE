import { useState } from "react";
import MapView from "./components/MapView";
import ScorePanel from "./components/ScorePanel";
import { IconLogo } from "./components/Icons";
import { analyze } from "./api/analyze";
import type { AnalysisResponse } from "./api/types";

export default function App() {
  const [point, setPoint] = useState<{ lat: number; lng: number } | null>(null);
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePick(lat: number, lng: number) {
    setPoint({ lat, lng });
    setLoading(true);
    setError(null);
    try {
      const resp = await analyze(lat, lng);
      setData(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <IconLogo size={26} />
          <div className="brand-text">
            <div className="brand-name">
              Grid<span>Site</span>Score
            </div>
            <div className="brand-sub">Infrastructure due-diligence · IT + EU grid</div>
          </div>
        </div>
        <div className="header-meta">
          <a
            href="https://github.com/valer0x/GRIDSITESCORE"
            target="_blank"
            rel="noreferrer"
            className="gh-link"
          >
            GitHub ↗
          </a>
        </div>
      </header>
      <div className="layout">
        <div className="map-wrap">
          <MapView point={point} onPick={handlePick} />
          <div className="legend">
            <div className="legend-title">Legend</div>
            <div className="legend-row"><span className="sw line380" /> ≥ 380 kV line</div>
            <div className="legend-row"><span className="sw line220" /> ≥ 220 kV line</div>
            <div className="legend-row"><span className="sw line110" /> 110 kV line</div>
            <div className="legend-row"><span className="sw sub" /> Substation (HV)</div>
            <div className="legend-row"><span className="sw plant-gas" /> Gas / oil plant</div>
            <div className="legend-row"><span className="sw plant-solar" /> Solar</div>
            <div className="legend-row"><span className="sw plant-wind" /> Wind</div>
            <div className="legend-row"><span className="sw plant-hydro" /> Hydro</div>
            <div className="legend-row"><span className="sw plant-nuclear" /> Nuclear</div>
            <div className="legend-row"><span className="sw dc" /> Data center</div>
            <div className="legend-note">Zoom in to load HV details</div>
          </div>
        </div>
        <aside className="panel">
          <ScorePanel data={data} loading={loading} error={error} />
        </aside>
      </div>
    </div>
  );
}
