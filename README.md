# GridSiteScore

**Explainable infrastructure due-diligence for energy and data-center sites.**

Click a point on a map of the Italian + neighboring-EU grid. In under a
second, get a weighted 0–100 score decomposed into grid access, energy
generation, digital infrastructure, and resilience — every number traceable
back to a rule in a YAML rubric, with a one-click PDF report.

![hero map — click to analyze a site](docs/screenshots/hero-map.png)

<details>
<summary><b>Table of contents</b></summary>

- [What it does](#what-it-does)
- [Why it exists](#why-it-exists)
- [Architecture](#architecture)
- [Scoring model](#scoring-model)
- [Stack](#stack)
- [Running locally](#running-locally)
- [Demo scenarios](#demo-scenarios)
- [Sample PDF report](#sample-pdf-report)
- [Design decisions & trade-offs](#design-decisions--trade-offs)
- [Roadmap](#roadmap)

</details>

---

## What it does

Input a `(lat, lng)`. The backend pulls the surrounding HV lines,
substations, power plants, and data centers within 10 / 50 / 100 km,
builds a NetworkX graph of the local transmission topology, and
returns a structured JSON:

- **Grid access** — nearest HV line, substation counts at multiple radii, line density
- **Energy** — installed capacity nearby, fuel-mix (Shannon diversity), renewable share
- **Digital** — data-center proximity, cluster count
- **Resilience** — average node degree, nearest-substation connectivity, articulation points
- **Score** — total 0–100 + per-category breakdown + **per-rule reasoning strings**

A React + Leaflet frontend layers the evidence on the map (toggleable
substations / transmission lines / power plants / data centers), shows
the decomposition in a sidebar, and exports a branded PDF report.

| | |
|---|---|
| ![Infrastructure layers on the map](docs/screenshots/infra-layers.png) | ![Score panel detail](docs/screenshots/panel-detail.png) |
| *Zoom in and every layer you see feeds the score* | *Every number decomposes to a rule + reason* |

---

## Why it exists

Early-stage site selection for a new data center, solar farm, or
industrial plant needs a **first-pass feasibility number** that's
defensible to a non-engineer stakeholder. Commercial due-diligence
tools are either black-box or locked to specific utilities.

GridSiteScore gives an **explainable, configurable, reproducible**
score on public data (WRI Global Power Plant DB, OpenStreetMap), so
anyone can audit *why* a location scored what it did and tune the
rubric to their specific deal.

Demo audience: site-selection teams at Eni, Enel, Terna, and EU data
center operators (Aruba, Retelit, Stack, Data4, Vantage).

---

## Architecture

Full diagram in [docs/architecture.md](docs/architecture.md). Short
version:

```
React + Leaflet ──► FastAPI ──► PostGIS 16 (+ NetworkX for graph)
                       │
                       ├── 4 per-category services (async SQLAlchemy)
                       ├── YAML-driven scoring engine
                       ├── TTLCache (per-coord + per-heatmap-bbox)
                       ├── PDF report (ReportLab, no system deps)
                       └── Heatmap endpoint (bbox × n-grid, concurrent)
```

Spatial filters use `ST_DWithin` on `geography(4326)` with GiST indexes
(spherical math, no projection bugs). The resilience graph's edge
list is built with a single `LATERAL` query letting the index do the
snap — see [the benchmark in design decisions](#perf-resilience-graph).

---

## Scoring model

Every rule maps a raw metric to a `[0,1]` sub-score via a
piecewise-linear `worst → best` curve, then rules are weighted within
a category, and categories are weighted into the 0–100 total.
**The rubric lives in [backend/scoring_config.yaml](backend/scoring_config.yaml)** —
edit it to retune; no code change needed.

```yaml
# excerpt
category_weights:
  grid_access: 0.30
  energy: 0.25
  digital: 0.15
  resilience: 0.30

rules:
  grid_access:
    - name: hv_line_proximity
      metric: nearest_hv_line_km
      weight: 0.50
      type: inverse_linear
      best: 5.0       # ≤5 km = full credit
      worst: 50.0     # ≥50 km = zero
```

Every response echoes the weights and rubric version so any number is
audit-reproducible:

```json
"score": {
  "total": 82,
  "breakdown": [ ...per-category, each with per-rule "reason" strings... ],
  "weights": {"grid_access": 0.30, "energy": 0.25, "digital": 0.15, "resilience": 0.30},
  "version": "1.1.0",
  "reasoning": [
    "[digital] Distance to nearest existing data center: 0.31 km (target ≤ 20 km) → 1.00/1.00",
    "[grid_access] Distance to nearest high-voltage transmission line: 2.95 km (target ≤ 5 km) → 1.00/1.00",
    ...
  ]
}
```

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18, TypeScript, Vite, Leaflet, react-leaflet |
| Backend  | Python 3.12+, FastAPI, SQLAlchemy 2 (async), GeoAlchemy2, asyncpg |
| Graph    | NetworkX (articulation points, degree metrics) |
| Geo      | PostGIS 16, Shapely, GeoPandas (seed only) |
| Rendering| ReportLab (PDF, pure Python — zero system deps) |
| Logging  | structlog (JSON lines, request-scoped context) |
| Testing  | pytest + httpx, 33 tests, DB-free via dependency-override mocks |

---

## Running locally

```bash
# 1. Database
cd backend
cp .env.example .env
docker compose up -d db

# 2. Backend (Python 3.12+)
python -m venv .venv && source .venv/Scripts/activate  # or .venv/bin/activate
pip install -r requirements.txt

# 3. Seed
python -m scripts.seed_data_centers          # instant (fixture shipped)
python -m scripts.seed_osm                   # ~1 min (Overpass API)
# WRI power-plants CSV must be downloaded once:
#   https://datasets.wri.org/dataset/globalpowerplantdatabase
#   drop it at scripts/fixtures/global_power_plant_database.csv
python -m scripts.seed_power_plants

# 4. Run
uvicorn app.main:app --reload                # backend on :8000

# 5. Frontend
cd ../frontend && npm install && npm run dev # on :5173
```

Open <http://localhost:5173>. Click the map. Toggle the **Heatmap** button
(top-left) for a pre-computed choropleth grid across the current viewport.

Test suite:

```bash
cd backend && pytest -q    # 33 passed in 2s
```

---

## Demo scenarios

The signal the scoring rubric produces when contrasting an urban hub
with a rural candidate — a useful benchmark that the model captures
reality, not just noise:

| Site | Lat, Lng | Total | Grid | Energy | Digital | Resilience |
|---|---|---:|---:|---:|---:|---:|
| **Milano** (dense urban, HV hub) | 45.46, 9.19 | **82** | 100 | 60 | 100 | 75 |
| **Sardegna** rural | 40.1, 9.3 | **66** | 91 | 36 | 0 | 100 |
| **Alpi centrali** remote | 46.0, 10.3 | ~40 | varies | high-hydro | 0 | varies |

The Milan/Sardinia contrast tracks intuition: Milan wins on urban-cluster
signals (HV density, DC proximity), rural Sardinia wins on topological
redundancy (simpler graph, no articulation points) but collapses on the
digital axis.

---

## Sample PDF report

One click in the UI produces a 1-page A4 due-diligence PDF with the
same branding as the app:

👉 [**docs/sample-report.pdf**](docs/sample-report.pdf)

Contents: radial score ring with grade letter (A/B/C/D/E), key drivers,
energy-mix donut chart, per-category bars with rule reasons, compact
4-card raw-indicators block, provenance footer.

![PDF report preview](docs/screenshots/pdf-report.png)

---

## Design decisions & trade-offs

### YAML rubric vs. Python DSL
Chose an external YAML over in-code thresholds so a non-engineer
reviewer can retune the scoring without a redeploy, and so the
response can echo the rubric version alongside the score. Trade-off:
no static type-checking on rule definitions — mitigated by a small
validator step in `ScoringConfig.from_yaml`.

### Public OSM data vs. authoritative ENTSO-E
Started with OSM Overpass for substations + HV lines because (a)
licence-compatible, (b) immediate access, (c) covers Italy densely.
Trade-off: OSM substations are often polygons with missing voltage
tags, so we centroid-snap with a 1500 m tolerance. A follow-up swap
to ENTSO-E Transparency Platform line data would tighten this.

### Resilience: articulation points vs. k-edge-connectivity
Articulation points are an `O(V+E)` proxy for single-point-of-failure
risk. True k-edge-connectivity would be more rigorous but costs more
per query. For a *first-pass* feasibility screen, articulation +
nearest-node degree is the right speed/signal trade-off; a switch to
k-edge-connectivity is ~50 lines and sits in the roadmap.

### <a name="perf-resilience-graph"></a>Perf: resilience graph construction
First cut was Python: load N substations + M line endpoints, snap each
endpoint to the nearest node via haversine. On Milan (~5k nodes, ~2.5k
lines) this took **116 s per request** and suffered correctness bugs
from pole-mounted distribution subs intruding. Second cut delegates
the snap to PostGIS via a single `LATERAL` join on the GiST index, and
only keeps substations that participate in at least one edge — that's
**<1 s** per request and a cleaner graph. See
[resilience.py](backend/app/services/resilience.py#L20-L60).

### SQL-side GeoJSON for map layers
`/features/*` endpoints use `ST_AsGeoJSON + jsonb_agg` to build the
full FeatureCollection server-side in a single round-trip. Faster than
marshalling rows into Python objects and re-serializing, and keeps
wire payloads bounded via LIMIT + bbox filters.

### Heatmap: concurrent sessions, per-cell reuse
The heatmap endpoint runs `analyze_point` on an n×n grid. A single
`AsyncSession` can't be shared across concurrent statements, so we
spawn one session per worker bounded by a `Semaphore(8)`. Each cell
hits the existing per-coord TTL cache, so pan/zoom overlap is free. A
separate bbox-keyed cache serves identical heatmap requests in O(1).

### PDF: ReportLab over WeasyPrint
WeasyPrint is prettier (CSS-driven) but brings Pango + Cairo + GDK
system dependencies that are painful on Windows and cumbersome in
Docker. ReportLab is pure Python — the same code renders identically
on Windows / Linux / Docker with zero apt installs. Layout is slightly
more manual but the result (see `docs/sample-report.pdf`) holds up.

---

## Roadmap

- [ ] **ENTSO-E line data** — replace OSM-derived topology for authoritative EU grid coverage
- [ ] **True k-edge-connectivity** replacing the articulation-point proxy
- [ ] **Multi-site comparison** — pin 2–3 candidates, see them side-by-side
- [ ] **Geocoding search** — type "Milano" instead of clicking
- [ ] **Water / land-use / IXP-latency layers** — deeper DC due-diligence axes
- [ ] **Deploy live** (Fly.io / Render + Supabase)

---

*Dataset credits: [WRI Global Power Plant Database](https://datasets.wri.org/dataset/globalpowerplantdatabase) (CC BY 4.0), [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL).*
