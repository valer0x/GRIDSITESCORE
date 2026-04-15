import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cached, set_cached
from app.config import get_settings
from app.logging_conf import get_logger
from app.models.schemas import AnalysisResponse, LatLng
from app.services.digital import compute_digital
from app.services.energy import compute_energy
from app.services.grid import compute_grid_access
from app.services.resilience import compute_resilience
from app.services.scoring import compute_score, load_config

log = get_logger(__name__)


async def analyze_point(
    session: AsyncSession, lat: float, lng: float
) -> AnalysisResponse:
    cached = get_cached(lat, lng)
    if cached is not None:
        log.info("analyze.cache_hit", lat=lat, lng=lng)
        return cached.model_copy(update={"cache_hit": True})

    t0 = time.perf_counter()

    # AsyncSession is single-connection; statements must be serialized.
    grid = await compute_grid_access(session, lat, lng)
    energy = await compute_energy(session, lat, lng)
    digital = await compute_digital(session, lat, lng)
    resilience = await compute_resilience(session, lat, lng)

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
