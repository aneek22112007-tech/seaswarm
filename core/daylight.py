"""Daylight margin for a search that has to be back before dark."""

from __future__ import annotations

from datetime import datetime


def daylight_margin(daylight_hours_left: float, estimated_hours: float) -> float:
    return round(daylight_hours_left - estimated_hours, 2)


def hours_between(start: datetime, end: datetime) -> float:
    return max(0.0, round((end - start).total_seconds() / 3600.0, 2))
