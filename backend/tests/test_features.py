"""Features endpoint contract tests — DB-free via dependency-override.

We stub the AsyncSession so the endpoint just exercises query-param
validation, response shape, and error handling. The SQL itself is
covered by the live integration checks in the README smoke tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_session


class _FakeResult:
    def __init__(self, geojson: dict | None):
        self._value = geojson

    def scalar(self):
        return self._value


class _FakeSession:
    def __init__(self, geojson: dict | None):
        self._value = geojson

    async def execute(self, _stmt, _params=None):
        return _FakeResult(self._value)


def _session_factory(geojson: dict | None):
    async def _s():
        yield _FakeSession(geojson)

    return _s


@pytest.fixture
def client_empty():
    from app.main import app

    app.dependency_overrides[get_session] = _session_factory(
        {"type": "FeatureCollection", "features": []}
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_substations_rejects_bad_bbox(client_empty):
    r = client_empty.get("/features/substations", params={"bbox": "1,2,3"})
    assert r.status_code == 400


def test_substations_rejects_inverted_bbox(client_empty):
    r = client_empty.get("/features/substations", params={"bbox": "10,45,5,40"})
    assert r.status_code == 400


def test_substations_accepts_valid_bbox(client_empty):
    r = client_empty.get(
        "/features/substations", params={"bbox": "9,45,10,46"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []


def test_lines_rejects_oor_lat(client_empty):
    r = client_empty.get("/features/transmission_lines", params={"bbox": "0,-91,1,1"})
    assert r.status_code == 400


def test_data_centers_no_bbox_returns_fc(client_empty):
    r = client_empty.get("/features/data_centers")
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"


def test_substations_limit_clamped(client_empty):
    r = client_empty.get(
        "/features/substations", params={"bbox": "9,45,10,46", "limit": 99999}
    )
    # Pydantic should reject > 5000
    assert r.status_code == 422


def test_substations_min_voltage_passes_through(client_empty):
    r = client_empty.get(
        "/features/substations",
        params={"bbox": "9,45,10,46", "min_voltage_kv": 220},
    )
    assert r.status_code == 200
