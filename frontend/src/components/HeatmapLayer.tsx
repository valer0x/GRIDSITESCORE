import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap } from "leaflet";
import { Rectangle, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { fetchHeatmap, type HeatmapResponse } from "../api/features";

function cellColor(score: number | null): string {
  if (score == null) return "rgba(148,163,184,0.1)";
  if (score >= 75) return "rgba(16, 185, 129, 0.55)";
  if (score >= 60) return "rgba(132, 204, 22, 0.55)";
  if (score >= 45) return "rgba(245, 158, 11, 0.55)";
  if (score >= 30) return "rgba(249, 115, 22, 0.55)";
  return "rgba(239, 68, 68, 0.55)";
}

function bboxStr(map: LeafletMap): string {
  const b = map.getBounds();
  return `${b.getWest().toFixed(5)},${b.getSouth().toFixed(5)},${b.getEast().toFixed(5)},${b.getNorth().toFixed(5)}`;
}

interface Props {
  enabled: boolean;
  resolution: number; // n x n grid
  onStateChange?: (s: "idle" | "loading" | "ready" | "error") => void;
}

export default function HeatmapLayer({ enabled, resolution, onStateChange }: Props) {
  const map = useMap();
  const [data, setData] = useState<HeatmapResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refetch = () => {
    if (!enabled) {
      setData(null);
      onStateChange?.("idle");
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    onStateChange?.("loading");
    fetchHeatmap(bboxStr(map), resolution, ac.signal)
      .then((d) => {
        setData(d);
        onStateChange?.("ready");
      })
      .catch((e) => {
        if (e.name === "AbortError") return;
        onStateChange?.("error");
        console.warn(e);
      });
  };

  useMapEvents({ moveend: refetch, zoomend: refetch });

  useEffect(() => {
    refetch();
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, resolution]);

  if (!enabled || !data) return null;

  const dy = data.cell_size_deg.lat;
  const dx = data.cell_size_deg.lng;

  return (
    <>
      {data.cells.map((c, idx) => {
        const bounds: [[number, number], [number, number]] = [
          [c.lat - dy / 2, c.lng - dx / 2],
          [c.lat + dy / 2, c.lng + dx / 2],
        ];
        return (
          <Rectangle
            key={idx}
            bounds={bounds}
            pathOptions={{
              color: "rgba(15, 23, 42, 0.25)",
              weight: 0.5,
              fillColor: cellColor(c.score),
              fillOpacity: 1,
            }}
          >
            <Tooltip direction="center" sticky>
              <div style={{ fontSize: 11 }}>
                <b>Score: {c.score ?? "—"}</b>
                <br />
                <span style={{ fontFamily: "monospace", color: "#64748b" }}>
                  {c.lat.toFixed(3)}, {c.lng.toFixed(3)}
                </span>
              </div>
            </Tooltip>
          </Rectangle>
        );
      })}
    </>
  );
}
