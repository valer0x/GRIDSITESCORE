from typing import Any

from cachetools import TTLCache

from app.config import get_settings

_settings = get_settings()

_analysis_cache: TTLCache[tuple[float, float], Any] = TTLCache(
    maxsize=_settings.cache_maxsize, ttl=_settings.cache_ttl_seconds
)


def _key(lat: float, lng: float) -> tuple[float, float]:
    # ~110 m grid at the equator, fine enough to dedupe repeated clicks.
    return (round(lat, 3), round(lng, 3))


def get_cached(lat: float, lng: float) -> Any | None:
    return _analysis_cache.get(_key(lat, lng))


def set_cached(lat: float, lng: float, value: Any) -> None:
    _analysis_cache[_key(lat, lng)] = value


def clear_cache() -> None:
    _analysis_cache.clear()
