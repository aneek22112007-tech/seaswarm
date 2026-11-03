"""Fuel, cost, time, and coverage. Every figure is a pure function of the geometry."""

from __future__ import annotations

import math

INR_PER_LITRE = 95.0
KM_PER_LITRE = 3.5
SEARCH_SPEED_KMH = 10.0
SWEEP_WIDTH_KM = 0.5


def wedge_area_km2(outer_km: float, angle_deg: float) -> float:
    return math.pi * outer_km**2 * (angle_deg / 360.0)


def estimate_hours(transit_km: float, search_hours: float) -> float:
    """Round trip at search speed, plus time on the sector."""
    return round((2.0 * transit_km) / SEARCH_SPEED_KMH + search_hours, 2)


def fuel_litres(transit_km: float, search_hours: float, boats: int) -> float:
    distance = (2.0 * transit_km + SEARCH_SPEED_KMH * search_hours) * boats
    return round(distance / KM_PER_LITRE, 1)


def cost_inr(litres: float) -> float:
    return round(litres * INR_PER_LITRE, 2)


def coverage_pct(outer_km: float, angle_deg: float, boats: int, search_hours: float) -> float:
    area = wedge_area_km2(outer_km, angle_deg)
    if area <= 0:
        return 0.0
    covered = SWEEP_WIDTH_KM * SEARCH_SPEED_KMH * search_hours * boats
    return round(min(100.0, 100.0 * covered / area), 1)
