import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Substation, TransmissionLine
from app.models.schemas import GridAccess
from app.utils.queries import point_geog, st_distance_m, st_dwithin


async def compute_grid_access(
    session: AsyncSession, lat: float, lng: float
) -> GridAccess:
    p = point_geog(lat, lng)

    nearest_line_stmt = select(
        func.min(st_distance_m(TransmissionLine.geog, lat, lng))
    )
    nearest_line_m: float | None = (await session.execute(nearest_line_stmt)).scalar()

    sub_10 = await session.scalar(
        select(func.count()).where(st_dwithin(Substation.geog, lat, lng, 10_000))
    )
    sub_50 = await session.scalar(
        select(func.count()).where(st_dwithin(Substation.geog, lat, lng, 50_000))
    )

    # Transmission-line density: sum of line lengths (km) within 50 km
    # divided by the area of that disk in km^2.
    length_m: float | None = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.ST_Length(
                        func.ST_Intersection(
                            TransmissionLine.geog,
                            func.ST_Buffer(p, 50_000),
                        )
                    )
                ),
                0.0,
            )
        ).where(st_dwithin(TransmissionLine.geog, lat, lng, 50_000))
    )
    area_km2 = math.pi * (50.0 ** 2)
    density = (float(length_m or 0.0) / 1000.0) / area_km2

    return GridAccess(
        nearest_hv_line_km=(
            round(float(nearest_line_m) / 1000.0, 3)
            if nearest_line_m is not None
            else None
        ),
        substations_10km=int(sub_10 or 0),
        substations_50km=int(sub_50 or 0),
        line_density_per_km2=round(density, 5),
    )
