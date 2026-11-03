"""Daylight left after a plan's estimated duration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.daylight import daylight_margin, hours_between

IST = timezone(timedelta(hours=5, minutes=30))


def test_margin_can_go_negative():
    assert daylight_margin(4.0, 1.8) == 2.2
    assert daylight_margin(1.0, 1.6) == -0.6


def test_hours_between_sunset_and_now():
    start = datetime(2026, 1, 15, 14, 30, tzinfo=IST)
    sunset = datetime(2026, 1, 15, 18, 30, tzinfo=IST)
    assert hours_between(start, sunset) == 4.0
    assert hours_between(sunset, start) == 0.0
