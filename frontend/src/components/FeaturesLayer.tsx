import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap } from "leaflet";
import {
  CircleMarker,
  LayerGroup,
  LayersControl,
  Polyline,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";
import {
  fetchDataCenters,
  fetchPowerPlants,
  fetchSubstations,
  fetchTransmissionLines,
  type DCProps,
  type FeatureCollection,
  type GeoJsonLineString,
  type GeoJsonPoint,
  type LineProps,
  type PlantProps,
  type SubstationProps,
} from "../api/features";

// Fuel → color tokens (match common energy-industry conventions).
const FUEL_COLORS: Record<string, string> = {
  solar: "#fbbf24",
  wind: "#38bdf8",
  hydro: "#2dd4bf",
  gas: "#f87171",
  oil: "#7f1d1d",
  coal: "#1f2937",
  nuclear: "#a855f7",
  biomass: "#84cc16",
  geothermal: "#f97316",
  waste: "#6b7280",
};

function plantColor(fuel: string | null): string {
  return FUEL_COLORS[(fuel || "").toLowerCase()] || "#e5e7eb";
}

function lineColor(v: number | null): string {
  if (v == null) return "#f59e0b";
  if (v >= 380) return "#ef4444";
  if (v >= 220) return "#f59e0b";
  return "#facc15";
}

function lineWeight(v: number | null): number {
  if (v == null) return 1;
  if (v >= 380) return 2.5;
  if (v >= 220) return 2;
  return 1.5;
}

function bboxStr(map: LeafletMap): string {
  const b = map.getBounds();
  return `${b.getWest().toFixed(5)},${b.getSouth().toFixed(5)},${b.getEast().toFixed(5)},${b.getNorth().toFixed(5)}`;
}

function useBboxFetch<G, P>(
  fetcher: (
    bbox: string,
    opts: { signal: AbortSignal; minVoltageKv?: number }
  ) => Promise<FeatureCollection<G, P>>,
  enabled: boolean,
  minZoomToLoad: number,
  minVoltageKv?: (zoom: number) => number | undefined
): FeatureCollection<G, P> | null {
  const map = useMap();
  const [data, setData] = useState<FeatureCollection<G, P> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refetch = () => {
    if (!enabled) {
      setData(null);
      return;
    }
    const zoom = map.getZoom();
    if (zoom < minZoomToLoad) {
      setData(null);
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const opts: { signal: AbortSignal; minVoltageKv?: number } = { signal: ac.signal };
    if (minVoltageKv) {
      const v = minVoltageKv(zoom);
      if (v !== undefined) opts.minVoltageKv = v;
    }
    fetcher(bboxStr(map), opts)
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") console.warn(e);
      });
  };

  useMapEvents({ moveend: refetch, zoomend: refetch });

  useEffect(() => {
    refetch();
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return data;
}

function SubstationsGroup({ enabled }: { enabled: boolean }) {
  const data = useBboxFetch<GeoJsonPoint, SubstationProps>(
    fetchSubstations,
    enabled,
    8,
    (z) => (z < 10 ? 220 : z < 11 ? 110 : undefined)
  );
  if (!data) return null;
  return (
    <>
      {data.features.map((f) => {
        const [lng, lat] = f.geometry.coordinates;
        const v = f.properties.voltage_kv;
        return (
          <CircleMarker
            key={f.properties.id}
            center={[lat, lng]}
            radius={3}
            pathOptions={{
              color: v && v >= 220 ? "#ef4444" : v && v >= 110 ? "#f59e0b" : "#94a3b8",
              weight: 1,
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <b>{f.properties.name || "Substation"}</b>
              <br />
              {v ? `${v} kV` : "voltage unknown"}
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

function LinesGroup({ enabled }: { enabled: boolean }) {
  const data = useBboxFetch<GeoJsonLineString, LineProps>(
    fetchTransmissionLines,
    enabled,
    7,
    (z) => (z < 9 ? 220 : undefined)
  );
  if (!data) return null;
  return (
    <>
      {data.features.map((f) => {
        const positions: [number, number][] = f.geometry.coordinates.map(
          ([lng, lat]) => [lat, lng]
        );
        return (
          <Polyline
            key={f.properties.id}
            positions={positions}
            pathOptions={{
              color: lineColor(f.properties.voltage_kv),
              weight: lineWeight(f.properties.voltage_kv),
              opacity: 0.85,
            }}
          >
            <Popup>
              {f.properties.voltage_kv
                ? `${f.properties.voltage_kv} kV transmission line`
                : "Transmission line (voltage unknown)"}
            </Popup>
          </Polyline>
        );
      })}
    </>
  );
}

function PlantsGroup({ enabled }: { enabled: boolean }) {
  const data = useBboxFetch<GeoJsonPoint, PlantProps>(fetchPowerPlants, enabled, 6);
  if (!data) return null;
  return (
    <>
      {data.features.map((f) => {
        const [lng, lat] = f.geometry.coordinates;
        const cap = f.properties.capacity_mw || 0;
        const radius = Math.max(4, Math.min(16, Math.sqrt(cap) * 0.6));
        return (
          <CircleMarker
            key={f.properties.id}
            center={[lat, lng]}
            radius={radius}
            pathOptions={{
              color: "#0f172a",
              weight: 1,
              fillColor: plantColor(f.properties.fuel),
              fillOpacity: 0.85,
            }}
          >
            <Popup>
              <b>{f.properties.name || "Power plant"}</b>
              <br />
              {f.properties.fuel || "fuel unknown"}
              {cap > 0 && <> · {cap.toFixed(0)} MW</>}
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

function DataCentersGroup({ enabled }: { enabled: boolean }) {
  const [data, setData] = useState<FeatureCollection<GeoJsonPoint, DCProps> | null>(
    null
  );
  useEffect(() => {
    if (!enabled) {
      setData(null);
      return;
    }
    const ac = new AbortController();
    fetchDataCenters({ signal: ac.signal })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") console.warn(e);
      });
    return () => ac.abort();
  }, [enabled]);
  if (!data) return null;
  return (
    <>
      {data.features.map((f) => {
        const [lng, lat] = f.geometry.coordinates;
        return (
          <CircleMarker
            key={f.properties.id}
            center={[lat, lng]}
            radius={6}
            pathOptions={{
              color: "#0f172a",
              weight: 1.5,
              fillColor: "#a855f7",
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <b>{f.properties.name}</b>
              <br />
              {f.properties.operator && (
                <>
                  {f.properties.operator}
                  <br />
                </>
              )}
              {f.properties.city}, {f.properties.country}
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

export default function FeaturesLayer() {
  const [show, setShow] = useState({
    substations: true,
    lines: true,
    plants: true,
    dcs: true,
  });
  return (
    <LayersControl position="topright" collapsed={false}>
      <LayersControl.Overlay checked name="Transmission lines">
        <LayerGroup
          eventHandlers={{
            add: () => setShow((s) => ({ ...s, lines: true })),
            remove: () => setShow((s) => ({ ...s, lines: false })),
          }}
        >
          <LinesGroup enabled={show.lines} />
        </LayerGroup>
      </LayersControl.Overlay>

      <LayersControl.Overlay checked name="Substations (HV)">
        <LayerGroup
          eventHandlers={{
            add: () => setShow((s) => ({ ...s, substations: true })),
            remove: () => setShow((s) => ({ ...s, substations: false })),
          }}
        >
          <SubstationsGroup enabled={show.substations} />
        </LayerGroup>
      </LayersControl.Overlay>

      <LayersControl.Overlay checked name="Power plants">
        <LayerGroup
          eventHandlers={{
            add: () => setShow((s) => ({ ...s, plants: true })),
            remove: () => setShow((s) => ({ ...s, plants: false })),
          }}
        >
          <PlantsGroup enabled={show.plants} />
        </LayerGroup>
      </LayersControl.Overlay>

      <LayersControl.Overlay checked name="Data centers">
        <LayerGroup
          eventHandlers={{
            add: () => setShow((s) => ({ ...s, dcs: true })),
            remove: () => setShow((s) => ({ ...s, dcs: false })),
          }}
        >
          <DataCentersGroup enabled={show.dcs} />
        </LayerGroup>
      </LayersControl.Overlay>
    </LayersControl>
  );
}
