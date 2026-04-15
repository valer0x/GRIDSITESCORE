"""Pure-Python geospatial helpers. No DB dependency — unit-testable."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bbox_around(lat: float, lng: float, radius_m: float) -> tuple[float, float, float, float]:
    """Approximate (min_lng, min_lat, max_lng, max_lat) around a point."""
    dlat = radius_m / 111_320.0
    dlng = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 1e-6))
    return (lng - dlng, lat - dlat, lng + dlng, lat + dlat)


def shannon_diversity(counts: dict[str, float]) -> float:
    """Shannon entropy (nats) of a categorical distribution."""
    total = sum(v for v in counts.values() if v > 0)
    if total <= 0:
        return 0.0
    h = 0.0
    for v in counts.values():
        if v <= 0:
            continue
        p = v / total
        h -= p * math.log(p)
    return h


RENEWABLE_FUELS = frozenset(
    {"solar", "wind", "hydro", "geothermal", "biomass", "wave_and_tidal"}
)


def is_renewable(fuel: str | None) -> bool:
    return (fuel or "").lower() in RENEWABLE_FUELS
