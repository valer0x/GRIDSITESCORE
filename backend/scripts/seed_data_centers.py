"""Seed data_centers from a curated JSON fixture.

No clean public dataset exists for data center locations, so we ship a
small curated list of well-known Italian / EU facilities. Replace with
an authoritative source (e.g. Data Center Map export) in production.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from scripts._common import build_engine, ensure_schema, truncate

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "data_centers.json"


def seed() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    engine = build_engine()
    ensure_schema(engine)
    truncate(engine, "data_centers")
    rows = [
        {
            "name": d["name"],
            "operator": d.get("operator"),
            "city": d.get("city"),
            "country": d.get("country"),
            "lat": d["lat"],
            "lng": d["lng"],
        }
        for d in data
    ]
    if rows:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO data_centers (name, operator, city, country, geog)
                    VALUES (:name, :operator, :city, :country,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
                    """
                ),
                rows,
            )
    print(f"Inserted {len(rows)} data centers")
    return len(rows)


if __name__ == "__main__":
    seed()
