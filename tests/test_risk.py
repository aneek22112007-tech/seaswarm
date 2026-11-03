"""The rough-sea flag names the clock from the weather mock."""

from __future__ import annotations

from core.risk import add_hours, risk_flags


def test_rough_seas_after_1630_when_the_search_runs_late():
    flags = risk_flags(
        wave_height_m=1.4,
        wind_speed_kn=14,
        sea_state=4,
        rough_after="16:30",
        start_hhmm="14:30",
        estimated_hours=2.5,
        daylight_margin_hours=1.5,
    )
    assert flags == ["rough seas after 16:30, recommend against"]


def test_short_daylight_and_strong_wind_are_separate_flags():
    flags = risk_flags(
        wave_height_m=2.2,
        wind_speed_kn=22,
        sea_state=2,
        rough_after="18:00",
        start_hhmm="14:30",
        estimated_hours=0.4,
        daylight_margin_hours=0.2,
    )
    assert "daylight margin under 30 minutes" in flags
    assert "wind at or above 20 kn" in flags
    assert "wave height at or above 2.0 m" in flags
    assert add_hours("14:30", 0.4) == "14:54"


def test_a_short_calm_search_has_no_flags():
    assert (
        risk_flags(
            wave_height_m=0.4,
            wind_speed_kn=8,
            sea_state=2,
            rough_after="16:30",
            start_hhmm="14:30",
            estimated_hours=0.5,
            daylight_margin_hours=3.5,
        )
        == []
    )
