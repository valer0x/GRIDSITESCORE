"""Endpoint smoke test.

We don't hit a real PostGIS — instead we monkeypatch each per-category
service to return canned values, so we can verify the request/response
contract, dependency wiring, and caching behaviour in isolation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import cache as cache_mod
from app.db import get_session
from app.models.schemas import (
    DigitalSection,
    EnergySection,
    GridAccess,
    ResilienceSection,
)


async def _fake_session():
    yield object()  # sentinel; services are mocked so session is unused


@pytest.fixture
def client(monkeypatch):
    async def fake_grid(_s, _lat, _lng):
        return GridAccess(
            nearest_hv_line_km=3.0,
            substations_10km=2,
            substations_50km=6,
            line_density_per_km2=0.08,
        )

    async def fake_energy(_s, _lat, _lng):
        return EnergySection(
            plants_50km=5,
            total_capacity_mw_50km=1500.0,
            mix_pct={"gas": 40, "solar": 30, "wind": 30},
            renewable_share=0.60,
            fuel_diversity_shannon=1.09,
        )

    async def fake_digital(_s, _lat, _lng):
        return DigitalSection(
            data_centers_50km=3,
            dc_count_100km=6,
            nearest_dc_km=8.0,
        )

    async def fake_resilience(_s, _lat, _lng):
        return ResilienceSection(
            nearby_nodes=12,
            avg_degree=2.7,
            nearest_substation_degree=3,
            articulation_points_20km=0,
            single_point_of_failure_risk="low",
        )

    monkeypatch.setattr(
        "app.services.orchestrator.compute_grid_access", fake_grid
    )
    monkeypatch.setattr("app.services.orchestrator.compute_energy", fake_energy)
    monkeypatch.setattr("app.services.orchestrator.compute_digital", fake_digital)
    monkeypatch.setattr(
        "app.services.orchestrator.compute_resilience", fake_resilience
    )

    cache_mod.clear_cache()

    from app.main import app

    app.dependency_overrides[get_session] = _fake_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "endpoints" in resp.json()


def test_analyze_shape(client):
    resp = client.get("/analyze", params={"lat": 45.4642, "lng": 9.1900})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) >= {
        "location",
        "grid_access",
        "energy",
        "digital",
        "resilience",
        "score",
    }
    assert data["location"] == {"lat": 45.4642, "lng": 9.19}
    score = data["score"]
    assert 0 <= score["total"] <= 100
    assert isinstance(score["breakdown"], list) and len(score["breakdown"]) == 4
    assert score["reasoning"], "should surface top reasoning bullets"
    for cat in score["breakdown"]:
        assert 0.0 <= cat["score_0_100"] <= 100.0
        assert cat["rules"], "each category must have explainable rules"
        for rule in cat["rules"]:
            assert "→" in rule["reason"]


def test_analyze_caches_second_call(client):
    r1 = client.get("/analyze", params={"lat": 45.4642, "lng": 9.1900}).json()
    r2 = client.get("/analyze", params={"lat": 45.4642, "lng": 9.1900}).json()
    assert r1["cache_hit"] is False
    assert r2["cache_hit"] is True
    assert r1["score"]["total"] == r2["score"]["total"]


def test_analyze_rejects_bad_latlng(client):
    resp = client.get("/analyze", params={"lat": 999, "lng": 0})
    assert resp.status_code == 422


def test_batch_endpoint(client):
    resp = client.post(
        "/analyze/batch",
        json={"points": [{"lat": 45.46, "lng": 9.19}, {"lat": 41.9, "lng": 12.5}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
