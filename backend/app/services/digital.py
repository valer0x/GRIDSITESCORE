from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import DataCenter
from app.models.schemas import DigitalSection
from app.utils.queries import st_distance_m, st_dwithin


async def compute_digital(
    session: AsyncSession, lat: float, lng: float
) -> DigitalSection:
    dc_50 = await session.scalar(
        select(func.count()).where(st_dwithin(DataCenter.geog, lat, lng, 50_000))
    )
    dc_100 = await session.scalar(
        select(func.count()).where(st_dwithin(DataCenter.geog, lat, lng, 100_000))
    )
    nearest_m: float | None = await session.scalar(
        select(func.min(st_distance_m(DataCenter.geog, lat, lng)))
    )

    return DigitalSection(
        data_centers_50km=int(dc_50 or 0),
        dc_count_100km=int(dc_100 or 0),
        nearest_dc_km=(
            round(float(nearest_m) / 1000.0, 3) if nearest_m is not None else None
        ),
        fiber_landing_km=None,
    )
