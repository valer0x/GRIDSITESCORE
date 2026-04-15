"""Resilience / redundancy heuristic.

Approach: build a NetworkX graph of substations within 100 km. Two
substations are connected if any transmission line has both endpoints
within `line_endpoint_snap_m` of the substations respectively. The
snap is performed in PostGIS (ST_DWithin on GiST indexes) so a single
SQL query produces the edge list — avoiding an O(N·M) Python loop.

Metrics:
- avg_degree: mean node degree (higher = more meshed)
- nearest_substation_degree: degree of the substation closest to the
  candidate site (dead-end if ≤ 1)
- articulation_points_20km: number of cut-vertices within 20 km whose
  removal would disconnect part of the graph — proxy for single-point
  of failure risk
"""

from __future__ import annotations

import networkx as nx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.schemas import ResilienceSection


_EDGES_SQL = text(
    """
    WITH p AS (
      SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography AS g
    ),
    nearby_lines AS (
      SELECT
        ST_StartPoint(t.geog::geometry)::geography AS start_g,
        ST_EndPoint(t.geog::geometry)::geography AS end_g
      FROM transmission_lines t, p
      WHERE ST_DWithin(t.geog, p.g, :graph_radius)
    )
    SELECT DISTINCT LEAST(a.id, b.id) AS a, GREATEST(a.id, b.id) AS b
    FROM nearby_lines l
    JOIN LATERAL (
      SELECT s.id FROM substations s
      WHERE ST_DWithin(s.geog, l.start_g, :snap)
      ORDER BY s.geog <-> l.start_g
      LIMIT 3
    ) a ON TRUE
    JOIN LATERAL (
      SELECT s.id FROM substations s
      WHERE ST_DWithin(s.geog, l.end_g, :snap)
      ORDER BY s.geog <-> l.end_g
      LIMIT 3
    ) b ON TRUE
    WHERE a.id <> b.id
    """
)

_NEAREST_GRAPH_NODE_SQL = text(
    """
    SELECT s.id
    FROM substations s
    WHERE s.id = ANY(:ids)
    ORDER BY s.geog <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
    LIMIT 1
    """
)

_ART_NEAR_SQL = text(
    """
    SELECT s.id
    FROM substations s
    WHERE s.id = ANY(:ids)
      AND ST_DWithin(
        s.geog,
        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
        :art_radius
      )
    """
)


def _risk_from(avg_degree: float, articulation: int) -> str:
    if articulation >= 2 or avg_degree < 1.5:
        return "high"
    if articulation >= 1 or avg_degree < 2.0:
        return "medium"
    return "low"


async def compute_resilience(
    session: AsyncSession, lat: float, lng: float
) -> ResilienceSection:
    settings = get_settings()
    params = {
        "lat": lat,
        "lng": lng,
        "graph_radius": settings.resilience_graph_radius_m,
        "snap": settings.line_endpoint_snap_m,
    }

    edge_rows = (await session.execute(_EDGES_SQL, params)).all()

    g: nx.Graph = nx.Graph()
    for r in edge_rows:
        g.add_edge(int(r.a), int(r.b))

    if g.number_of_nodes() == 0:
        return ResilienceSection(
            nearby_nodes=0,
            avg_degree=0.0,
            nearest_substation_degree=0,
            articulation_points_20km=0,
            single_point_of_failure_risk="high",
        )

    degrees = [d for _, d in g.degree()]
    avg_degree = sum(degrees) / len(degrees)

    node_ids = list(g.nodes)
    nearest_id = (
        await session.execute(
            _NEAREST_GRAPH_NODE_SQL, {**params, "ids": node_ids}
        )
    ).scalar()
    nearest_degree = int(g.degree(nearest_id)) if nearest_id in g else 0

    art_near_rows = (
        await session.execute(
            _ART_NEAR_SQL,
            {
                "lat": lat,
                "lng": lng,
                "ids": node_ids,
                "art_radius": settings.resilience_articulation_radius_m,
            },
        )
    ).all()
    art_near_ids = {int(r.id) for r in art_near_rows}
    articulation_set = set(nx.articulation_points(g))
    art_near = len(articulation_set & art_near_ids)

    return ResilienceSection(
        nearby_nodes=g.number_of_nodes(),
        avg_degree=round(avg_degree, 3),
        nearest_substation_degree=nearest_degree,
        articulation_points_20km=art_near,
        single_point_of_failure_risk=_risk_from(avg_degree, art_near),
    )
