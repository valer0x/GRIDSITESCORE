"""GeoJSON feature endpoints — surface the raw infrastructure the scorer
uses, so demo viewers can see the evidence behind any given score.

All endpoints are bbox-filtered and limited to keep payloads bounded.
GeoJSON is built server-side with PostGIS `ST_AsGeoJSON` + `json_agg`
so a single round-trip returns a ready-to-render FeatureCollection.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(prefix="/features", tags=["features"])


def _parse_bbox(s: str) -> tuple[float, float, float, float]:
    try:
        parts = [float(p) for p in s.split(",")]
    except ValueError as e:
        raise HTTPException(400, f"invalid bbox: {e}") from e
    if len(parts) != 4:
        raise HTTPException(400, "bbox must be minlng,minlat,maxlng,maxlat")
    w, s_, e, n = parts
    if w >= e or s_ >= n:
        raise HTTPException(400, "bbox is empty or inverted")
    if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s_ <= 90 and -90 <= n <= 90):
        raise HTTPException(400, "bbox out of lat/lng range")
    return w, s_, e, n


def _empty() -> dict:
    return {"type": "FeatureCollection", "features": []}


async def _fetch_geojson(
    session: AsyncSession, sql: str, params: dict
) -> dict:
    row = (await session.execute(text(sql), params)).scalar()
    return row or _empty()


@router.get("/substations")
async def substations(
    bbox: str = Query(...),
    limit: int = Query(2000, ge=1, le=5000),
    min_voltage_kv: float | None = Query(None, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    w, s, e, n = _parse_bbox(bbox)
    sql = """
        SELECT jsonb_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(jsonb_agg(f), '[]'::jsonb)
        )
        FROM (
          SELECT jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geog::geometry)::jsonb,
            'properties', jsonb_build_object(
              'id', id, 'name', name, 'voltage_kv', voltage_kv
            )
          ) AS f
          FROM substations
          WHERE geog && ST_MakeEnvelope(:w, :s, :e, :n, 4326)::geography
            AND (CAST(:min_v AS float) IS NULL OR voltage_kv IS NULL OR voltage_kv >= CAST(:min_v AS float))
          LIMIT :limit
        ) x
    """
    return await _fetch_geojson(
        session,
        sql,
        {"w": w, "s": s, "e": e, "n": n, "limit": limit, "min_v": min_voltage_kv},
    )


@router.get("/transmission_lines")
async def transmission_lines(
    bbox: str = Query(...),
    limit: int = Query(1500, ge=1, le=3000),
    min_voltage_kv: float | None = Query(None, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    w, s, e, n = _parse_bbox(bbox)
    sql = """
        SELECT jsonb_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(jsonb_agg(f), '[]'::jsonb)
        )
        FROM (
          SELECT jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geog::geometry)::jsonb,
            'properties', jsonb_build_object('id', id, 'voltage_kv', voltage_kv)
          ) AS f
          FROM transmission_lines
          WHERE geog && ST_MakeEnvelope(:w, :s, :e, :n, 4326)::geography
            AND (CAST(:min_v AS float) IS NULL OR voltage_kv IS NULL OR voltage_kv >= CAST(:min_v AS float))
          LIMIT :limit
        ) x
    """
    return await _fetch_geojson(
        session,
        sql,
        {"w": w, "s": s, "e": e, "n": n, "limit": limit, "min_v": min_voltage_kv},
    )


@router.get("/power_plants")
async def power_plants(
    bbox: str = Query(...),
    limit: int = Query(1500, ge=1, le=3000),
    session: AsyncSession = Depends(get_session),
) -> dict:
    w, s, e, n = _parse_bbox(bbox)
    sql = """
        SELECT jsonb_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(jsonb_agg(f), '[]'::jsonb)
        )
        FROM (
          SELECT jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geog::geometry)::jsonb,
            'properties', jsonb_build_object(
              'id', id, 'name', name, 'fuel', fuel,
              'capacity_mw', capacity_mw, 'country', country
            )
          ) AS f
          FROM power_plants
          WHERE geog && ST_MakeEnvelope(:w, :s, :e, :n, 4326)::geography
          LIMIT :limit
        ) x
    """
    return await _fetch_geojson(
        session,
        sql,
        {"w": w, "s": s, "e": e, "n": n, "limit": limit},
    )


@router.get("/data_centers")
async def data_centers(
    bbox: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # Data centers are a small set (~30) — if no bbox, return all.
    if bbox is None:
        sql = """
            SELECT jsonb_build_object(
              'type', 'FeatureCollection',
              'features', COALESCE(jsonb_agg(f), '[]'::jsonb)
            )
            FROM (
              SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(geog::geometry)::jsonb,
                'properties', jsonb_build_object(
                  'id', id, 'name', name, 'operator', operator,
                  'city', city, 'country', country
                )
              ) AS f
              FROM data_centers
            ) x
        """
        return await _fetch_geojson(session, sql, {})
    w, s, e, n = _parse_bbox(bbox)
    sql = """
        SELECT jsonb_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(jsonb_agg(f), '[]'::jsonb)
        )
        FROM (
          SELECT jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geog::geometry)::jsonb,
            'properties', jsonb_build_object(
              'id', id, 'name', name, 'operator', operator,
              'city', city, 'country', country
            )
          ) AS f
          FROM data_centers
          WHERE geog && ST_MakeEnvelope(:w, :s, :e, :n, 4326)::geography
        ) x
    """
    return await _fetch_geojson(
        session, sql, {"w": w, "s": s, "e": e, "n": n}
    )
