"""Seed power_plants from the WRI Global Power Plant Database (v1.3.0).

CSV source (CC BY 4.0):
  https://datasets.wri.org/dataset/globalpowerplantdatabase

Usage:
  python -m scripts.seed_power_plants path/to/global_power_plant_database.csv \
      [--countries ITA FRA CHE AUT SVN]

If no path is given, tries scripts/fixtures/global_power_plant_database.csv.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from scripts._common import build_engine, ensure_schema, truncate

DEFAULT_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "global_power_plant_database.csv"
)
DEFAULT_COUNTRIES = ("ITA", "FRA", "CHE", "AUT", "SVN", "HRV", "SMR", "VAT", "MCO")


def _clean_fuel(v: str | float | None) -> str | None:
    if not isinstance(v, str) or not v.strip():
        return None
    return v.strip().lower().replace(" ", "_")


def seed(csv_path: Path, countries: tuple[str, ...]) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Power plant CSV not found at {csv_path}. Download from "
            "https://datasets.wri.org/dataset/globalpowerplantdatabase"
        )

    df = pd.read_csv(csv_path, low_memory=False)
    df = df[df["country"].isin(countries)]
    df = df.dropna(subset=["latitude", "longitude"])

    engine = build_engine()
    ensure_schema(engine)
    truncate(engine, "power_plants")

    rows = [
        {
            "source_id": str(r["gppd_idnr"]),
            "name": (r.get("name") or None),
            "country": r["country"],
            "fuel": _clean_fuel(r.get("primary_fuel")),
            "capacity_mw": (
                float(r["capacity_mw"]) if pd.notna(r["capacity_mw"]) else None
            ),
            "lat": float(r["latitude"]),
            "lng": float(r["longitude"]),
        }
        for _, r in df.iterrows()
    ]

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO power_plants
                    (source_id, name, country, fuel, capacity_mw, geog)
                VALUES
                    (:source_id, :name, :country, :fuel, :capacity_mw,
                     ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
                """
            ),
            rows,
        )
    print(f"Inserted {len(rows)} power plants from {csv_path.name}")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(DEFAULT_PATH))
    ap.add_argument("--countries", nargs="+", default=list(DEFAULT_COUNTRIES))
    args = ap.parse_args()
    seed(Path(args.path), tuple(args.countries))


if __name__ == "__main__":
    main()
