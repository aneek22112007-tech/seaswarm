"""Pinned fuel, cost, time, and coverage figures."""

from __future__ import annotations

import pytest

from core.cost import cost_inr, coverage_pct, estimate_hours, fuel_litres


def test_one_boat_search_cost():
    assert estimate_hours(4, 1) == 1.8
    assert fuel_litres(4, 1, 1) == 5.1
    assert cost_inr(5.1) == 484.5


def test_coverage_is_capped_at_100():
    assert coverage_pct(5, 40, 1, 1) == pytest.approx(57.3)
    assert coverage_pct(1, 10, 5, 5) == 100.0
