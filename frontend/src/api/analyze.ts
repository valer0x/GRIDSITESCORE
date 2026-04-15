import type { AnalysisResponse } from "./types";

// Dev: Vite proxies /api → localhost:8000 (see vite.config.ts).
// Prod: set VITE_API_BASE to the deployed backend URL (e.g. Render).
const BASE = import.meta.env.VITE_API_BASE || "/api";

export async function analyze(lat: number, lng: number): Promise<AnalysisResponse> {
  const resp = await fetch(`${BASE}/analyze?lat=${lat}&lng=${lng}`);
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Backend ${resp.status}: ${body}`);
  }
  return resp.json();
}

export function pdfReportUrl(lat: number, lng: number): string {
  return `${BASE}/analyze/report.pdf?lat=${lat}&lng=${lng}`;
}
