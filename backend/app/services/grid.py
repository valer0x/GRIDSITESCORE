import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import GridAccess

# Single-round-trip query: fetch nearest-line distance, two substation
# counts, and total HV-line length within 50 km in one statement. The
# length is summed unclipped (ST_Length of the whole line) rather than
# clipped against a 50 km disk — a cheap density proxy that skips the
# expensive ST_Intersection(ST_Buffer(...)).
_GRID_SQL = text(
    """
    WITH p AS (
      SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography AS g
    )
    SELECT
      (SELECT MIN(ST_Distance(t.geog, p.g))
         FROM transmission_lines t, p)                                       AS nearest_line_m,
      (SELECT COUNT(*) FROM substations s, p
         WHERE ST_DWithin(s.geog, p.g, 10000))                               AS sub_10,
      (SELECT COUNT(*) FROM substations s, p
         WHERE ST_DWithin(s.geog, p.g, 50000))                               AS sub_50,
      (SELECT COALESCE(SUM(ST_Length(t.geog)), 0)
         FROM transmission_lines t, p
         WHERE ST_DWithin(t.geog, p.g, 50000))                               AS line_length_m
    """
)

_AREA_50KM_KM2 = math.pi * (50.0 ** 2)


async def compute_grid_access(
    session: AsyncSession, lat: float, lng: float
) -> GridAccess:
    row = (await session.execute(_GRID_SQL, {"lat": lat, "lng": lng})).one()
    nearest_m = row.nearest_line_m
    density = (float(row.line_length_m or 0.0) / 1000.0) / _AREA_50KM_KM2
    return GridAccess(
        nearest_hv_line_km=(
            round(float(nearest_m) / 1000.0, 3) if nearest_m is not None else None
        ),
        substations_10km=int(row.sub_10 or 0),
        substations_50km=int(row.sub_50 or 0),
        line_density_per_km2=round(density, 5),
    )
