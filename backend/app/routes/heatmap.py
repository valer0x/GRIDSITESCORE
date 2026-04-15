"""Heatmap endpoint: evaluates the full scoring pipeline on a grid of
points inside a bbox and returns `[ {lat, lng, score} ]` for the UI to
render as a choropleth.

Performance notes:
- A single AsyncSession is not safe for concurrent queries, so we spawn
  one session per worker and bound concurrency with a Semaphore.
- The existing per-point cache (TTL keyed on rounded lat/lng) makes
  repeated heatmap calls on overlapping regions near-instant.
- A separate in-process cache stores full heatmap responses keyed on
  (bbox rounded, grid_n) so identical requests return in O(1).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.services.orchestrator import analyze_point

router = APIRouter(prefix="/heatmap", tags=["heatmap"])

_heatmap_cache: TTLCache[tuple, dict] = TTLCache(
    maxsize=64, ttl=get_settings().cache_ttl_seconds
)


@dataclass(frozen=True, slots=True)
class _BBox:
    w: float
    s: float
    e: float
    n: float


def _parse_bbox(raw: str) -> _BBox:
    try:
        parts = [float(p) for p in raw.split(",")]
    except ValueError as e:
        raise HTTPException(400, f"invalid bbox: {e}") from e
    if len(parts) != 4:
        raise HTTPException(400, "bbox must be minlng,minlat,maxlng,maxlat")
    b = _BBox(*parts)
    if b.w >= b.e or b.s >= b.n:
        raise HTTPException(400, "bbox is empty or inverted")
    if not (-180 <= b.w <= 180 and -180 <= b.e <= 180 and -90 <= b.s <= 90 and -90 <= b.n <= 90):
        raise HTTPException(400, "bbox out of range")
    return b


def _grid_points(bbox: _BBox, n: int) -> list[tuple[float, float]]:
    """Return (lat, lng) pairs on an n×n grid, evenly spaced with a
    half-cell inset so points don't sit on the bbox edge."""
    points = []
    for i in range(n):
        for j in range(n):
            frac_x = (j + 0.5) / n
            frac_y = (i + 0.5) / n
            lng = bbox.w + frac_x * (bbox.e - bbox.w)
            lat = bbox.s + frac_y * (bbox.n - bbox.s)
            points.append((lat, lng))
    return points


async def _analyze_one(
    sem: asyncio.Semaphore, lat: float, lng: float
) -> dict:
    async with sem:
        try:
            # Orchestrator manages its own per-service sessions.
            resp = await analyze_point(None, lat, lng)
            return {
                "lat": round(lat, 4),
                "lng": round(lng, 4),
                "score": resp.score.total,
            }
        except Exception:
            return {"lat": round(lat, 4), "lng": round(lng, 4), "score": None}


@router.get("")
async def heatmap(
    bbox: str = Query(..., description="minlng,minlat,maxlng,maxlat"),
    n: int = Query(12, ge=3, le=20, description="grid resolution (n × n cells)"),
    concurrency: int = Query(8, ge=1, le=16),
) -> dict:
    b = _parse_bbox(bbox)
    key = (
        round(b.w, 3), round(b.s, 3), round(b.e, 3), round(b.n, 3), n,
    )
    if key in _heatmap_cache:
        return {**_heatmap_cache[key], "cache_hit": True}

    pts = _grid_points(b, n)
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*[_analyze_one(sem, lat, lng) for lat, lng in pts])

    payload = {
        "bbox": [b.w, b.s, b.e, b.n],
        "n": n,
        "cells": results,
        "cell_size_deg": {
            "lng": (b.e - b.w) / n,
            "lat": (b.n - b.s) / n,
        },
        "cache_hit": False,
    }
    _heatmap_cache[key] = {**payload, "cache_hit": False}
    return payload
