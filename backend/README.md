# Infrastructure Due Diligence Tool — Backend

Early-stage site-analysis API for energy, data center, and industrial
projects. Takes a `(lat, lng)` and returns a structured, weighted,
explainable 0-100 score across four categories: **grid access**,
**energy**, **digital infrastructure**, **resilience**.

Built with FastAPI + PostGIS + GeoAlchemy2 + NetworkX. Targets the
Italian / southern-EU grid footprint (Terna / ENTSO-E) by default.

---

## Architecture

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan
│   ├── config.py               # pydantic-settings (DB, radii, cache)
│   ├── db.py                   # async SQLAlchemy engine + session
│   ├── cache.py                # TTL cache keyed on rounded (lat,lng)
│   ├── logging_conf.py         # structlog JSON
│   ├── routes/
│   │   ├── analyze.py          # GET /analyze, POST /analyze/batch
│   │   └── health.py           # GET /health with table row counts
│   ├── services/
│   │   ├── grid.py             # HV line proximity, substation counts, density
│   │   ├── energy.py           # nearby capacity, mix, Shannon diversity
│   │   ├── digital.py          # data center proximity & counts
│   │   ├── resilience.py       # NetworkX graph, articulation points, degree
│   │   ├── scoring.py          # YAML-driven rule engine (see below)
│   │   └── orchestrator.py     # asyncio.gather + cache + log
│   ├── models/
│   │   ├── orm.py              # spatial tables with GiST indexes
│   │   └── schemas.py          # Pydantic response models
│   └── utils/
│       ├── geo.py              # haversine, bbox, Shannon, renewables set
│       └── queries.py          # ST_DWithin / ST_Distance helpers
├── scripts/
│   ├── seed_power_plants.py    # WRI Global Power Plant DB loader
│   ├── seed_osm.py             # OSM Overpass → substations + lines
│   ├── seed_data_centers.py    # curated JSON fixture loader
│   └── fixtures/
│       └── data_centers.json   # ~30 curated EU DC locations
├── tests/
│   ├── test_geo.py             # pure-function geo
│   ├── test_scoring.py         # normalization, weighting, YAML override
│   └── test_analyze.py         # endpoint contract + caching
├── scoring_config.yaml         # external rubric (edit to retune)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Scoring engine (the core design decision)

Scoring is **rule-based, configurable, normalized, and explainable** —
suitable for defending a number in front of investment or permitting
stakeholders.

- **Configurable** — every threshold lives in
  [`scoring_config.yaml`](scoring_config.yaml). Adding a new rule is
  one YAML entry plus one field in `_collect_metrics`. No scoring code
  changes are required to retune.
- **Normalized** — each rule maps its raw metric to a `[0,1]` sub-score
  using a piecewise-linear `worst → best` curve (`linear` or
  `inverse_linear`). Clamping keeps every rule on the same scale.
- **Weighted** — each rule has a weight within its category; categories
  are weighted into the final score via `category_weights`. Weights are
  renormalized defensively so the total is always in `[0, 100]`.
- **Explainable** — every rule emits a `reason` string
  (e.g. `"Distance to nearest HV line: 3.20 km (target ≤ 5 km) → 0.93/1.00"`)
  and the response surfaces the 4 most decisive rules as top-level
  `reasoning` bullets.

Every response includes the full per-rule breakdown, the weights used,
and the scoring-config `version`, so any number in the output can be
traced back to the rubric that produced it.

### Data sources

| Dataset | Source | License | Loaded by |
|---|---|---|---|
| Power plants | WRI Global Power Plant DB v1.3.0 | CC BY 4.0 | `seed_power_plants.py` |
| Substations | OSM `power=substation` via Overpass | ODbL | `seed_osm.py` |
| Transmission lines | OSM `power=line`, voltage ≥ 110 kV | ODbL | `seed_osm.py` |
| Data centers | Curated JSON fixture (~30 EU DCs) | manual | `seed_data_centers.py` |

---

## Run locally

### Option A — Docker Compose (recommended)

```bash
cd backend
cp .env.example .env
docker compose up --build
```

PostGIS lives on `localhost:5432`; API on `localhost:8000`
(Swagger at <http://localhost:8000/docs>).

Then seed the database (from the host, against the containerized DB):

```bash
# 1. Power plants — download the WRI CSV first
#    https://datasets.wri.org/dataset/globalpowerplantdatabase
#    Put it at scripts/fixtures/global_power_plant_database.csv
docker compose exec api python -m scripts.seed_power_plants

# 2. OSM substations + lines (bbox = Italy + neighbors)
docker compose exec api python -m scripts.seed_osm

# 3. Data centers
docker compose exec api python -m scripts.seed_data_centers
```

### Option B — native Python 3.12

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start a local PostGIS however you like (Docker is easiest):
docker run -d --name idd-db -p 5432:5432 \
  -e POSTGRES_USER=idd -e POSTGRES_PASSWORD=idd -e POSTGRES_DB=idd \
  postgis/postgis:16-3.4

export DATABASE_URL=postgresql+asyncpg://idd:idd@localhost:5432/idd
python -m scripts.seed_power_plants
python -m scripts.seed_osm
python -m scripts.seed_data_centers

uvicorn app.main:app --reload
```

---

## Usage

### Single point

```bash
curl "http://localhost:8000/analyze?lat=45.4642&lng=9.1900" | jq
```

Response (abridged):

```jsonc
{
  "location": {"lat": 45.4642, "lng": 9.19},
  "grid_access": {
    "nearest_hv_line_km": 1.8, "substations_10km": 4,
    "substations_50km": 22, "line_density_per_km2": 0.094
  },
  "energy": {
    "plants_50km": 18, "total_capacity_mw_50km": 3420.5,
    "mix_pct": {"gas": 48.1, "solar": 22.3, "hydro": 18.0, "wind": 11.6},
    "renewable_share": 0.519, "fuel_diversity_shannon": 1.24
  },
  "digital": {
    "data_centers_50km": 11, "dc_count_100km": 15, "nearest_dc_km": 2.1
  },
  "resilience": {
    "nearby_nodes": 34, "avg_degree": 2.47,
    "nearest_substation_degree": 3, "articulation_points_20km": 0,
    "single_point_of_failure_risk": "low"
  },
  "score": {
    "total": 87,
    "breakdown": [
      {
        "name": "grid_access", "weight": 0.30, "score_0_100": 94.0,
        "weighted_contribution": 28.2,
        "rules": [
          {
            "name": "hv_line_proximity",
            "label": "Distance to nearest high-voltage transmission line",
            "raw_value": 1.8, "unit": "km",
            "weight": 0.5, "normalized_score": 0.93,
            "weighted_contribution": 0.465,
            "reason": "Distance to nearest high-voltage transmission line: 1.80 km (target ≤ 5 km) → 0.93/1.00"
          }
          // ...
        ]
      }
      // ...
    ],
    "weights": {"grid_access": 0.30, "energy": 0.25, "digital": 0.15, "resilience": 0.30},
    "version": "1.1.0",
    "reasoning": [
      "[digital] Distance to nearest existing data center: 2.10 km (target ≤ 20 km) → 1.00/1.00",
      "[grid_access] Distance to nearest high-voltage transmission line: 1.80 km (target ≤ 5 km) → 0.93/1.00",
      "[resilience] Articulation points (single-points-of-failure) within 20 km: 0 count (target ≤ 0 count) → 1.00/1.00",
      "[energy] Renewable share of nearby generation: 0.52 fraction (target ≥ 0.3 fraction) → 1.00/1.00"
    ]
  },
  "cache_hit": false,
  "duration_ms": 84.2
}
```

### Batch

```bash
curl -X POST http://localhost:8000/analyze/batch \
  -H "content-type: application/json" \
  -d '{"points":[{"lat":45.46,"lng":9.19},{"lat":41.9,"lng":12.5}]}'
```

### Health

```bash
curl http://localhost:8000/health
# {"status":"ok","counts":{"power_plants":8421,"substations":1733,...}}
```

---

## Tuning the rubric

Open [`scoring_config.yaml`](scoring_config.yaml) and adjust weights or
thresholds. Bump `version` so clients can distinguish runs. No code
redeploy needed — just restart the process (or mount the file and send
`SIGHUP` if you add hot-reload).

Example — prioritize data center / fiber clustering over resilience:

```yaml
category_weights:
  grid_access: 0.25
  energy: 0.15
  digital: 0.35       # was 0.15
  resilience: 0.25    # was 0.30
```

---

## Tests

```bash
cd backend
pytest -q
```

The test suite is DB-free: scoring and geo are pure functions, and the
endpoint test uses FastAPI dependency overrides + monkeypatched services.

---

## PDF report

`GET /analyze/report.pdf?lat=&lng=` returns a 1-2 page due-diligence report
rendered with ReportLab (pure Python, no system deps). Mirrors the web UI:
total score, per-category bars with rule reasons, raw indicators table.

```bash
curl -o report.pdf "http://localhost:8000/analyze/report.pdf?lat=45.4642&lng=9.1900"
```

## Frontend

See [../frontend/](../frontend/) — React + Leaflet + Vite SPA. Click anywhere
on the map to analyze a site; the panel shows the total score, top drivers,
per-category breakdowns, raw indicators, and a one-click PDF export.

```bash
cd ../frontend
npm install
npm run dev            # http://localhost:5173, proxies /api → :8000
```

## Next improvements

- Replace OSM-derived topology with ENTSO-E Transparency Platform for
  authoritative EU line data.
- True k-edge-connectivity instead of articulation-point heuristic.
- Add water availability, land-use, and IXP-latency layers for deeper
  data center due diligence.
- Heatmap overlay: score a dense grid and render as a choropleth layer.
- Per-tenant auth + rate limiting for external exposure.
