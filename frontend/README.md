# Infrastructure Due Diligence — Frontend

React + Leaflet + Vite + TypeScript. Click the map to analyze a site;
the panel shows total score, top drivers, category breakdowns, raw
indicators, and a one-click PDF export.

## Run

```bash
npm install
npm run dev            # http://localhost:5173
```

Requires the backend running on `http://localhost:8000` (default).
Vite proxies `/api/*` → `http://localhost:8000/*` so there are no CORS
issues in dev.

## Build

```bash
npm run build          # emits dist/
npm run preview        # serve dist/ at :4173
```

## Structure

```
frontend/
├── src/
│   ├── main.tsx                 # React entry
│   ├── App.tsx                  # layout + state
│   ├── styles.css               # dark theme
│   ├── api/
│   │   ├── analyze.ts           # fetch + PDF URL builder
│   │   └── types.ts             # mirrors backend Pydantic schemas
│   └── components/
│       ├── MapView.tsx          # Leaflet map with click capture
│       ├── ScorePanel.tsx       # right-side analysis panel
│       └── CategoryBreakdown.tsx # expandable rule list per category
├── index.html
├── vite.config.ts               # /api proxy to backend
└── tsconfig.json
```

## Design notes

- Types in [src/api/types.ts](src/api/types.ts) are a 1:1 mirror of the
  backend `AnalysisResponse` Pydantic schema. Keep them in sync when the
  backend contract evolves.
- Every rule's human-readable `reason` string is rendered verbatim —
  explainability comes from the backend, the frontend only surfaces it.
- Score colors (green ≥75, amber ≥50, orange ≥25, red <25) are shared
  between the UI and the PDF report.
