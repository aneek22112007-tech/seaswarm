"""Exactly three options, and a rejected option is replaced rather than dropped."""

from __future__ import annotations

from core.conflicts import assignment_conflict
from core.drift import drift_cone
from core.plans import build_options
from core.sectors import split_sectors


def _options(rejected=None):
    cone = drift_cone(
        lat=17.8136,
        lon=73.0394,
        hours=2,
        wind_from_deg=270,
        wind_speed_kn=14,
        current_to_deg=200,
        current_speed_kn=0.6,
        seed=42,
    )
    return build_options(
        sectors=split_sectors(cone, count=3),
        boats=["Chandra-2", "Harnai-Queen", "Meerabai"],
        rejected=rejected,
        wave_height_m=1.4,
        wind_speed_kn=14,
        sea_state=4,
        rough_after="16:30",
        start_hhmm="14:30",
        daylight_hours_left=4.0,
    )


def test_planner_returns_three_priced_options():
    options = _options()
    assert [option.option_id for option in options] == ["A", "B", "C"]
    assert options[0].boats == ("Chandra-2",)
    assert options[1].boats == ("Chandra-2", "Harnai-Queen")
    assert len(options[2].boats) == 3
    assert options[0].fuel_litres > 0
    assert options[0].cost_inr == round(options[0].fuel_litres * 95, 2)
    assert options[2].coverage_pct >= options[0].coverage_pct


def test_rejecting_option_b_revises_it_and_keeps_three():
    revised = _options({"b"})
    assert len(revised) == 3
    assert revised[1].title.startswith("revised:")
    assert revised[1].boats == ("Chandra-2",)
    assert len(revised[1].sector_names) == 2


def test_a_second_boat_on_a_taken_sector_is_refused_out_loud():
    message = assignment_conflict({"Sector-1": "Meerabai"}, "Sector-1", "Chandra-2")
    assert message == (
        "Conflict: Sector-1 is already assigned to Meerabai. "
        "Refusing to assign Chandra-2 as well."
    )
    assert assignment_conflict({"Sector-1": "Meerabai"}, "Sector-1", "Meerabai") is None
    assert assignment_conflict({"Sector-1": None}, "Sector-1", "Meerabai") is None
