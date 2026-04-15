import type { AnalysisResponse } from "./types";

const BASE = "/api";

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
