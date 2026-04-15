import math

import pytest

from app.utils.geo import (
    bbox_around,
    haversine_m,
    is_renewable,
    shannon_diversity,
)


def test_haversine_known_distance():
    # Milan → Rome, ~477 km great-circle
    d = haversine_m(45.4642, 9.1900, 41.9028, 12.4964)
    assert 470_000 <= d <= 485_000


def test_haversine_zero():
    assert haversine_m(0, 0, 0, 0) == pytest.approx(0.0, abs=1e-6)


def test_bbox_sizes_match_radius():
    min_lng, min_lat, max_lng, max_lat = bbox_around(45.0, 9.0, 10_000)
    # lat span ~ 2 * 10km / 111.32km ≈ 0.18 deg
    assert (max_lat - min_lat) == pytest.approx(2 * 10_000 / 111_320.0, rel=1e-3)
    # lng span scales with cos(lat)
    expected_lng = 2 * 10_000 / (111_320.0 * math.cos(math.radians(45.0)))
    assert (max_lng - min_lng) == pytest.approx(expected_lng, rel=1e-3)


def test_shannon_uniform_is_ln_n():
    h = shannon_diversity({"a": 1, "b": 1, "c": 1, "d": 1})
    assert h == pytest.approx(math.log(4), rel=1e-6)


def test_shannon_single_class_is_zero():
    assert shannon_diversity({"a": 5}) == 0.0


def test_shannon_empty_is_zero():
    assert shannon_diversity({}) == 0.0


def test_is_renewable():
    assert is_renewable("Solar")
    assert is_renewable("wind")
    assert not is_renewable("gas")
    assert not is_renewable(None)
