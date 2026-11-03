"""Split a drift cone into named search sectors. The center sector is the most likely."""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.drift import DriftCone, move_km, velocity_components


@dataclass(frozen=True)
class SectorSlice:
    name: str
    probability: float
    bearing_from: float
    bearing_to: float
    angle_deg: float
    outer_km: float
    mid_km: float
    polygon: tuple[tuple[float, float], ...]


def probability_weights(count: int) -> list[float]:
    if count < 1:
        raise ValueError("a cone needs at least one sector")
    half = (count - 1) / 2
    return [math.exp(-0.5 * (index - half) ** 2) for index in range(count)]


def normalize_percent(weights: list[float]) -> list[float]:
    total = sum(weights)
    percents = [round(100.0 * weight / total, 1) for weight in weights]
    remainder = round(100.0 - sum(percents), 1)
    center = len(percents) // 2
    percents[center] = round(percents[center] + remainder, 1)
    return percents


def split_sectors(cone: DriftCone, *, count: int = 3) -> list[SectorSlice]:
    """Cut the cone into `count` wedges from the last known position."""
    weights = normalize_percent(probability_weights(count))
    width = (2 * cone.spread_deg) / count
    start = cone.bearing_deg - cone.spread_deg
    outer = cone.distance_km + cone.radius_km
    sectors: list[SectorSlice] = []
    for index in range(count):
        bearing_from = start + index * width
        bearing_to = bearing_from + width
        polygon = [_point(cone, bearing_from, outer), _point(cone, bearing_to, outer)]
        origin = (round(cone.origin_lat, 5), round(cone.origin_lon, 5))
        sectors.append(
            SectorSlice(
                name=f"Sector-{index + 1}",
                probability=weights[index],
                bearing_from=round(bearing_from, 3),
                bearing_to=round(bearing_to, 3),
                angle_deg=round(width, 3),
                outer_km=round(outer, 3),
                mid_km=round(cone.distance_km, 3),
                polygon=(origin, polygon[0], polygon[1], origin),
            )
        )
    return sectors


def _point(cone: DriftCone, bearing: float, distance_km: float) -> tuple[float, float]:
    east, north = velocity_components(bearing, distance_km)
    lat, lon = move_km(cone.origin_lat, cone.origin_lon, east, north)
    return round(lat, 5), round(lon, 5)
