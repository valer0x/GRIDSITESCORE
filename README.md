# GridSiteScore

**Infrastructure due-diligence tool for energy and data-center sites.**

Input a `(lat, lng)`, get a **weighted, explainable 0–100 score** across
grid access, energy generation, digital infrastructure, and resilience —
with a one-click PDF due-diligence report.

Built for realistic use on the **Italian + neighboring-EU grid** (Terna /
ENTSO-E footprint), using public datasets (WRI Global Power Plant DB,
OpenStreetMap).

## What it does

Click anywhere on the map → the backend pulls substations, HV lines,
power plants, and data centers within 10/50/100 km, builds a NetworkX
graph of the local transmission topology, computes a rule-based score
against a YAML-configured rubric, and returns a structured JSON with
per-rule reasoning.

| Input | → | Output |
|---|---|---|
| `(lat, lng)` | | total score 0–100, category breakdowns, rule-level reasons, PDF export |

**Example (Milano vs. rural Sardegna)**:

| Site | Total | Grid | Energy | Digital | Resilience |
|---|---:|---:|---:|---:|---:|
| Milano `45.46, 9.19` | 82 | 100 | 60 | 100 | 75 |
| Sardegna `40.1, 9.3` | 66 | 91 | 36 | 0 | 100 |

The contrast is intentional — Milano wins on urban-cluster signals
(grid density, data-center proximity); rural Sardegna wins on
topological redundancy but collapses on the digital axis.

## Stack

- **Backend:** FastAPI · SQLAlchemy 2 (async) · GeoAlchemy2 · PostGIS 16 · NetworkX · ReportLab
- **Frontend:** React · Leaflet · Vite · TypeScript
- **Scoring:** YAML-driven rule engine — normalized, weighted, explainable
- **Data:** WRI Global Power Plant DB · OSM Overpass · curated data-center fixture

## Quick start

```bash
# 1. Database
cd backend
cp .env.example .env
docker compose up -d db

# 2. Backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
python -m scripts.seed_data_centers   # instant
python -m scripts.seed_osm            # ~1 min (Overpass)
# Power plants: drop WRI CSV into scripts/fixtures/ then:
python -m scripts.seed_power_plants
uvicorn app.main:app --reload         # :8000

# 3. Frontend
cd ../frontend
npm install && npm run dev            # :5173
```

Open <http://localhost:5173> and click the map.

## Layout

```
backend/   FastAPI + PostGIS service — see backend/README.md
frontend/  React + Leaflet SPA — see frontend/README.md
```

## Design highlights

- **Explainable scoring**: every total decomposes into categories →
  rules → raw values + reasoning strings. No black box.
- **Configurable**: edit [backend/scoring_config.yaml](backend/scoring_config.yaml)
  to retune thresholds or weights without touching code.
- **PostGIS-native**: spatial filters run `ST_DWithin` on GiST-indexed
  `geography(4326)` columns — spherical distance, no reprojection bugs.
- **SQL-side graph construction**: resilience's edge list comes from a
  single `LATERAL` query using the GiST index, keeping a 100-km graph
  build under a second (down from ~2 minutes in the first-cut Python
  implementation).
- **Test discipline**: 26 tests cover scoring boundaries, YAML override,
  PDF render, geo utilities, and endpoint contracts — all DB-free via
  dependency-override mocks.

## Roadmap

- Heatmap overlay: pre-compute a grid of scores, render as choropleth.
- ENTSO-E Transparency Platform for authoritative EU line data.
- True k-edge-connectivity instead of the articulation-point proxy.
- Water / land-use / IXP-latency layers for deeper DC due diligence.
- Auth + rate limiting for public exposure.
