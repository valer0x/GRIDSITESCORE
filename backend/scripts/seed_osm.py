"""Seed substations + transmission_lines from OpenStreetMap via Overpass.

Default bbox covers Italy + bordering countries. Runs two chunked queries
to stay under Overpass rate limits. Results are cached as GeoJSON under
scripts/fixtures/ so reruns are instant and CI can run offline.

Usage:
  python -m scripts.seed_osm [--bbox minlat minlng maxlat maxlng] [--offline]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests
from shapely.geometry import LineString, Point, mapping, shape
from sqlalchemy import text

from scripts._common import build_engine, ensure_schema, truncate

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SUBSTATIONS_GEOJSON = FIXTURES_DIR / "substations.geojson"
LINES_GEOJSON = FIXTURES_DIR / "transmission_lines.geojson"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_BBOX = (35.0, 5.0, 48.0, 19.0)  # (S, W, N, E) — Italy + neighbors
MIN_VOLTAGE = 110_000  # 110 kV and up


def _overpass(query: str, timeout: int = 180) -> dict:
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _fetch_substations(bbox: tuple[float, float, float, float]) -> list[dict]:
    s, w, n, e = bbox
    q = f"""
    [out:json][timeout:180];
    (
      node["power"="substation"]({s},{w},{n},{e});
      way["power"="substation"]({s},{w},{n},{e});
    );
    out center tags;
    """
    data = _overpass(q)
    features = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        if el["type"] == "node":
            lat, lng = el["lat"], el["lon"]
        else:
            c = el.get("center") or {}
            lat, lng = c.get("lat"), c.get("lon")
        if lat is None or lng is None:
            continue
        voltage = _parse_voltage(tags.get("voltage"))
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "source_id": f"{el['type']}/{el['id']}",
                    "name": tags.get("name"),
                    "voltage_kv": voltage,
                },
                "geometry": mapping(Point(lng, lat)),
            }
        )
    return features


def _fetch_lines(bbox: tuple[float, float, float, float]) -> list[dict]:
    s, w, n, e = bbox
    q = f"""
    [out:json][timeout:240];
    way["power"="line"]["voltage"]({s},{w},{n},{e});
    out geom tags;
    """
    data = _overpass(q)
    features = []
    for el in data.get("elements", []):
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        tags = el.get("tags", {})
        v = _parse_voltage(tags.get("voltage"))
        if v is None or v * 1000 < MIN_VOLTAGE:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in geom]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "source_id": f"way/{el['id']}",
                    "voltage_kv": v,
                },
                "geometry": mapping(LineString(coords)),
            }
        )
    return features


def _parse_voltage(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        # Multi-voltage tags like "220000;380000" — take the max.
        return max(float(x) for x in raw.split(";") if x.strip().isdigit()) / 1000.0
    except ValueError:
        return None


def _write_geojson(path: Path, features: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )


def _read_geojson(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["features"]


def _insert_substations(features: list[dict]) -> int:
    engine = build_engine()
    ensure_schema(engine)
    truncate(engine, "substations")
    rows = []
    for f in features:
        pt = shape(f["geometry"])
        rows.append(
            {
                "source_id": f["properties"].get("source_id"),
                "name": f["properties"].get("name"),
                "voltage_kv": f["properties"].get("voltage_kv"),
                "lng": pt.x,
                "lat": pt.y,
            }
        )
    if rows:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO substations (source_id, name, voltage_kv, geog)
                    VALUES (:source_id, :name, :voltage_kv,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
                    """
                ),
                rows,
            )
    print(f"Inserted {len(rows)} substations")
    return len(rows)


def _insert_lines(features: list[dict]) -> int:
    engine = build_engine()
    ensure_schema(engine)
    truncate(engine, "transmission_lines")
    rows = []
    for f in features:
        ls = shape(f["geometry"])
        rows.append(
            {
                "source_id": f["properties"].get("source_id"),
                "voltage_kv": f["properties"].get("voltage_kv"),
                "wkt": ls.wkt,
            }
        )
    if rows:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO transmission_lines (source_id, voltage_kv, geog, geom)
                    VALUES (:source_id, :voltage_kv,
                        ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography,
                        ST_SetSRID(ST_GeomFromText(:wkt), 4326))
                    """
                ),
                rows,
            )
    print(f"Inserted {len(rows)} transmission lines")
    return len(rows)


def seed(
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX, offline: bool = False
) -> None:
    if offline:
        if not SUBSTATIONS_GEOJSON.exists() or not LINES_GEOJSON.exists():
            raise FileNotFoundError(
                "Offline mode requires cached GeoJSON in scripts/fixtures/"
            )
        subs = _read_geojson(SUBSTATIONS_GEOJSON)
        lines = _read_geojson(LINES_GEOJSON)
    else:
        print("Fetching substations from Overpass...")
        subs = _fetch_substations(bbox)
        _write_geojson(SUBSTATIONS_GEOJSON, subs)
        time.sleep(2)
        print("Fetching transmission lines from Overpass...")
        lines = _fetch_lines(bbox)
        _write_geojson(LINES_GEOJSON, lines)

    _insert_substations(subs)
    _insert_lines(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, default=list(DEFAULT_BBOX))
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    seed(tuple(args.bbox), offline=args.offline)


if __name__ == "__main__":
    main()
