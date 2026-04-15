export interface GeoJsonPoint {
  type: "Point";
  coordinates: [number, number];
}

export interface GeoJsonLineString {
  type: "LineString";
  coordinates: [number, number][];
}

export interface Feature<G, P> {
  type: "Feature";
  geometry: G;
  properties: P;
}

export interface FeatureCollection<G, P> {
  type: "FeatureCollection";
  features: Feature<G, P>[];
}

export interface SubstationProps {
  id: number;
  name: string | null;
  voltage_kv: number | null;
}

export interface LineProps {
  id: number;
  voltage_kv: number | null;
}

export interface PlantProps {
  id: number;
  name: string | null;
  fuel: string | null;
  capacity_mw: number | null;
  country: string | null;
}

export interface DCProps {
  id: number;
  name: string;
  operator: string | null;
  city: string | null;
  country: string | null;
}

const BASE = import.meta.env.VITE_API_BASE || "/api";

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { signal });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export function fetchSubstations(
  bbox: string,
  opts: { minVoltageKv?: number; limit?: number; signal?: AbortSignal } = {}
) {
  const qs = new URLSearchParams({ bbox });
  if (opts.minVoltageKv !== undefined) qs.set("min_voltage_kv", String(opts.minVoltageKv));
  if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
  return fetchJson<FeatureCollection<GeoJsonPoint, SubstationProps>>(
    `/features/substations?${qs.toString()}`,
    opts.signal
  );
}

export function fetchTransmissionLines(
  bbox: string,
  opts: { minVoltageKv?: number; limit?: number; signal?: AbortSignal } = {}
) {
  const qs = new URLSearchParams({ bbox });
  if (opts.minVoltageKv !== undefined) qs.set("min_voltage_kv", String(opts.minVoltageKv));
  if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
  return fetchJson<FeatureCollection<GeoJsonLineString, LineProps>>(
    `/features/transmission_lines?${qs.toString()}`,
    opts.signal
  );
}

export function fetchPowerPlants(
  bbox: string,
  opts: { limit?: number; signal?: AbortSignal } = {}
) {
  const qs = new URLSearchParams({ bbox });
  if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
  return fetchJson<FeatureCollection<GeoJsonPoint, PlantProps>>(
    `/features/power_plants?${qs.toString()}`,
    opts.signal
  );
}

export function fetchDataCenters(opts: { signal?: AbortSignal } = {}) {
  return fetchJson<FeatureCollection<GeoJsonPoint, DCProps>>(
    `/features/data_centers`,
    opts.signal
  );
}

export interface HeatmapCell {
  lat: number;
  lng: number;
  score: number | null;
}
export interface HeatmapResponse {
  bbox: [number, number, number, number];
  n: number;
  cells: HeatmapCell[];
  cell_size_deg: { lng: number; lat: number };
  cache_hit: boolean;
}

export function fetchHeatmap(
  bbox: string,
  n: number,
  signal?: AbortSignal
): Promise<HeatmapResponse> {
  return fetchJson<HeatmapResponse>(`/heatmap?bbox=${bbox}&n=${n}`, signal);
}
