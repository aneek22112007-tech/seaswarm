"""Drift is leeway plus current, and the seed only changes the outline."""

from __future__ import annotations

import pytest

from core.drift import cone_radius_km, cone_spread_deg, drift_cone, drift_vectors


def test_leeway_blows_downwind_and_current_is_added():
    vectors = drift_vectors(270, 10, 180, 1)
    assert vectors.blow_to_deg == 90
    assert vectors.leeway_east_kmh == pytest.approx(0.5556, abs=1e-4)
    assert vectors.leeway_north_kmh == pytest.approx(0, abs=1e-9)
    assert vectors.current_east_kmh == pytest.approx(0, abs=1e-9)
    assert vectors.current_north_kmh == pytest.approx(-1.852, abs=1e-4)
    assert vectors.east_kmh == pytest.approx(0.5556, abs=1e-4)
    assert vectors.north_kmh == pytest.approx(-1.852, abs=1e-4)


def test_cone_center_moves_with_the_vectors():
    cone = drift_cone(
        lat=17.8,
        lon=73.1,
        hours=2,
        wind_from_deg=270,
        wind_speed_kn=10,
        current_to_deg=180,
        current_speed_kn=1,
        heading_deg=250,
        seed=42,
    )
    assert cone.center_lon > 73.1
    assert cone.center_lat < 17.8
    assert cone.east_km == pytest.approx(1.1112, abs=1e-3)
    assert cone.north_km == pytest.approx(-3.704, abs=1e-3)
    assert cone.radius_km == 0.95
    assert cone.spread_deg == 24
    assert cone.heading_deg == 250
    assert cone.polygon[0] == cone.polygon[-1]


def test_radius_and_spread_grow_with_hours_and_then_cap():
    assert cone_radius_km(2) == 0.95
    assert cone_spread_deg(2) == 24
    assert cone_spread_deg(20) == 70


def test_seed_reproduces_the_polygon_without_moving_the_center(monkeypatch):
    kwargs = dict(
        lat=17.8136,
        lon=73.0394,
        hours=2,
        wind_from_deg=270,
        wind_speed_kn=14,
        current_to_deg=200,
        current_speed_kn=0.6,
    )
    first = drift_cone(**kwargs, seed=42)
    second = drift_cone(**kwargs, seed=42)
    other = drift_cone(**kwargs, seed=7)
    assert first.polygon == second.polygon
    assert first.polygon != other.polygon
    assert first.center_lat == other.center_lat
    assert first.center_lon == other.center_lon
    monkeypatch.setenv("SEASWARM_SEED", "7")
    from_env = drift_cone(**kwargs)
    assert from_env.polygon == other.polygon


def test_negative_hours_are_rejected():
    with pytest.raises(ValueError):
        drift_cone(
            lat=17.8,
            lon=73.1,
            hours=-1,
            wind_from_deg=0,
            wind_speed_kn=0,
            current_to_deg=0,
            current_speed_kn=0,
        )
