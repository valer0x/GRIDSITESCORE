import asyncio
import time

from app.cache import get_cached, set_cached
from app.config import get_settings
from app.db import SessionLocal
from app.logging_conf import get_logger
from app.models.schemas import AnalysisResponse, LatLng
from app.services.digital import compute_digital
from app.services.energy import compute_energy
from app.services.grid import compute_grid_access
from app.services.resilience import compute_resilience
from app.services.scoring import compute_score, load_config

log = get_logger(__name__)


async def _with_session(coro_factory, lat: float, lng: float):
    """Run one service on a dedicated AsyncSession so the four can run
    in parallel. A single AsyncSession can't be shared across concurrent
    statements — asyncpg raises. Opening a session per service and
    letting the pool reuse connections is the cheapest fix."""
    async with SessionLocal() as session:
        return await coro_factory(session, lat, lng)


async def analyze_point(
    _session_unused, lat: float, lng: float
) -> AnalysisResponse:
    """The `_session_unused` parameter is kept for call-site compatibility
    with the per-request Depends(get_session) pattern, but we open our
    own sessions so we can run the four services concurrently."""
    cached = get_cached(lat, lng)
    if cached is not None:
        log.info("analyze.cache_hit", lat=lat, lng=lng)
        return cached.model_copy(update={"cache_hit": True})

    t0 = time.perf_counter()

    grid, energy, digital, resilience = await asyncio.gather(
        _with_session(compute_grid_access, lat, lng),
        _with_session(compute_energy, lat, lng),
        _with_session(compute_digital, lat, lng),
        _with_session(compute_resilience, lat, lng),
    )

    config = load_config(get_settings().scoring_config_path)
    score = compute_score(config, grid, energy, digital, resilience)

    duration_ms = (time.perf_counter() - t0) * 1000.0
    response = AnalysisResponse(
        location=LatLng(lat=lat, lng=lng),
        grid_access=grid,
        energy=energy,
        digital=digital,
        resilience=resilience,
        score=score,
        cache_hit=False,
        duration_ms=round(duration_ms, 2),
    )
    set_cached(lat, lng, response)

    log.info(
        "analyze.computed",
        lat=lat,
        lng=lng,
        score_total=score.total,
        duration_ms=duration_ms,
    )
    return response
