import { useState } from "react";
import HeatmapLayer from "./HeatmapLayer";
import { IconSparkles } from "./Icons";

type State = "idle" | "loading" | "ready" | "error";

export default function HeatmapControl() {
  const [enabled, setEnabled] = useState(false);
  const [resolution, setResolution] = useState(10);
  const [state, setState] = useState<State>("idle");

  return (
    <>
      <HeatmapLayer
        enabled={enabled}
        resolution={resolution}
        onStateChange={setState}
      />
      <div className="heatmap-ctrl">
        <button
          className={`heatmap-toggle ${enabled ? "on" : ""}`}
          onClick={() => setEnabled((v) => !v)}
          type="button"
        >
          <IconSparkles size={14} />
          <span>Heatmap</span>
          {state === "loading" && <span className="heatmap-spinner" />}
        </button>
        {enabled && (
          <div className="heatmap-res">
            <label>Resolution</label>
            <input
              type="range"
              min={6}
              max={16}
              value={resolution}
              onChange={(e) => setResolution(Number(e.target.value))}
            />
            <span className="heatmap-res-val">{resolution}×{resolution}</span>
          </div>
        )}
        {enabled && (
          <div className="heatmap-scale">
            <span className="hs-label">low</span>
            <span className="hs-grad" />
            <span className="hs-label">high</span>
          </div>
        )}
      </div>
    </>
  );
}
