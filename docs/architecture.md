# Architecture

## Request flow — `GET /analyze?lat=&lng=`

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend (React + Vite)                      │
│                                                                      │
│   ┌──────────┐   click    ┌────────────┐    GET /analyze   ┌──────┐  │
│   │ MapView  │ ─────────► │  App.tsx   │ ─────────────────►│ API  │  │
│   │ Leaflet  │            │  state     │                   │ base │  │
│   └──────────┘            └────────────┘ ◄─ AnalysisResp. ─└──────┘  │
│                                  │                                   │
│                         render ScorePanel (ring + breakdown + PDF)   │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTP/JSON
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI async)                        │
│                                                                      │
│   routes/analyze.py  ──►  services/orchestrator.py                   │
│                                   │                                  │
│             ┌─────────────────────┼──────────────────────┐           │
│             ▼                     ▼                      ▼           │
│      services/grid.py      services/energy.py     services/digital  │
│      services/resilience   ──────┐                                  │
│             │                    │                                   │
│             ▼                    ▼                                   │
│      PostGIS (ST_DWithin,   NetworkX (avg_degree,                    │
│      GiST indexes on        articulation points,                     │
│      geography(4326))       nearest-substation degree)               │
│             │                                                        │
│             ▼                                                        │
│      services/scoring.py  ──►  YAML rule engine                      │
│       normalize → weight → reason → total                            │
│             │                                                        │
│             ▼                                                        │
│   cachetools TTLCache keyed on round(lat,lng,3)                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                          PostGIS 16 (Docker)
                          ├── power_plants (2.8k, WRI)
                          ├── substations (83k, OSM)
                          ├── transmission_lines (31k, OSM ≥ 110 kV)
                          └── data_centers (30, curated)
```

## Scoring rubric

```
┌─ scoring_config.yaml ──────────────────────────────────────┐
│                                                            │
│  category_weights:                                         │
│    grid_access:  0.30  energy:     0.25                    │
│    digital:      0.15  resilience: 0.30                    │
│                                                            │
│  rules.grid_access:                                        │
│    - hv_line_proximity   (inverse_linear best=5 worst=50)  │
│    - substations_50km    (linear        worst=0 best=5)    │
│    - substations_10km    (linear        worst=0 best=2)    │
│                                                            │
│  rules.energy:                                             │
│    - installed_capacity  (linear        worst=0 best=1000) │
│    - fuel_diversity      (linear Shannon, best=1.3)        │
│    - renewable_share     (linear best=0.3)                 │
│                                                            │
│  rules.digital:                                            │
│    - nearest_dc          (inverse best=20  worst=200)      │
│    - dc_count_100km      (linear  best=3)                  │
│                                                            │
│  rules.resilience:                                         │
│    - avg_node_degree     (linear  best=2.5)                │
│    - nearest_sub_degree  (linear  best=3)                  │
│    - articulation_20km   (inverse best=0 worst=3)          │
│                                                            │
└────────────────────────────────────────────────────────────┘

  each raw metric → [0..1] via piecewise-linear worst→best
                 ┌─────────┐     ┌──────────┐     ┌────────────┐
                 │ rule    │ w×  │ category │ w×  │ total 0-100 │
                 │ score   │──►  │ 0-100    │──►  │ + reasoning │
                 └─────────┘     └──────────┘     └────────────┘
```

## Resilience graph construction

```
  1.  ST_DWithin(transmission_lines.geog, point, 100 km)
            │
            ▼
  2.  For each line, LATERAL join on substations within
      1500 m of each endpoint (snap tolerance)
            │
            ▼
  3.  Distinct (a, b) pairs where a ≠ b  →  edge list
            │
            ▼
  4.  networkx.Graph(edges)
            │
            ▼
  5.  Metrics:
       • avg_degree (∑ deg / |V|)
       • nearest_substation_degree (KNN to candidate)
       • articulation_points ∩ subs within 20 km
       • SPOF risk: f(avg_degree, articulation_count)
```

Before the LATERAL-based SQL refactor, the Python-side
O(N·M) haversine loop took ~116 s on Milano. The SQL
version lands in **<1 s** by letting PostGIS's GiST
index do the snapping.
