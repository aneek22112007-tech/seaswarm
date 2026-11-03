"""Sectors tile the cone and put the highest probability in the middle."""

from __future__ import annotations

import pytest

from core.drift import drift_cone
from core.sectors import normalize_percent, split_sectors


def _cone():
    return drift_cone(
        lat=17.8136,
        lon=73.0394,
        hours=2,
        wind_from_deg=270,
        wind_speed_kn=14,
        current_to_deg=200,
        current_speed_kn=0.6,
        seed=42,
    )


def test_three_sectors_cover_the_spread_and_sum_to_100():
    cone = _cone()
    sectors = split_sectors(cone, count=3)
    assert [sector.name for sector in sectors] == ["Sector-1", "Sector-2", "Sector-3"]
    assert sum(sector.probability for sector in sectors) == pytest.approx(100.0)
    assert sum(sector.angle_deg for sector in sectors) == pytest.approx(cone.spread_deg * 2)
    assert sectors[1].probability > sectors[0].probability
    assert (
        sectors[1].probability == sectors[2].probability
        or sectors[1].probability > sectors[2].probability
    )
    assert sectors[0].polygon[0] == (round(cone.origin_lat, 5), round(cone.origin_lon, 5))


def test_percentages_absorb_rounding_on_the_center_sector():
    assert sum(normalize_percent([1, 2, 1])) == pytest.approx(100.0)
