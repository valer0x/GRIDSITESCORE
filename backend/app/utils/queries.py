"""Reusable SQL fragments for PostGIS spatial queries.

All distances and radii are meters on `geography(..., 4326)` columns,
which gives us spherical math without reprojection bugs.
"""

from geoalchemy2 import Geography
from sqlalchemy import func


def point_geog(lat: float, lng: float):
    """ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography"""
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography)


def st_dwithin(col, lat: float, lng: float, radius_m: float):
    return func.ST_DWithin(col, point_geog(lat, lng), radius_m)


def st_distance_m(col, lat: float, lng: float):
    return func.ST_Distance(col, point_geog(lat, lng))
