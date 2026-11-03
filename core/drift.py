"""Leeway plus current, integrated over the hours a boat has been overdue.

The cone center does not use the random seed. The seed only phases the outline
sample so two runs with SEASWARM_SEED draw the same polygon.
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass

KNOT_TO_KMH = 1.852
LEEWAY_FACTOR = 0.03
KM_PER_DEG_LAT = 110.574


def km_per_deg_lon(lat_deg: float) -> float:
    return 111.320 * math.cos(math.radians(lat_deg))


def move_km(lat: float, lon: float, east_km: float, north_km: float) -> tuple[float, float]:
    return (
        lat + north_km / KM_PER_DEG_LAT,
        lon + east_km / km_per_deg_lon(lat),
    )


def velocity_components(bearing_deg: float, speed_kmh: float) -> tuple[float, float]:
    """East and north components. Bearing 0 is north, 90 is east."""
    radians = math.radians(bearing_deg)
    return speed_kmh * math.sin(radians), speed_kmh * math.cos(radians)


@dataclass(frozen=True)
class DriftVectors:
    leeway_east_kmh: float
    leeway_north_kmh: float
    current_east_kmh: float
    current_north_kmh: float
    east_kmh: float
    north_kmh: float
    blow_to_deg: float


def drift_vectors(
    wind_from_deg: float,
    wind_speed_kn: float,
    current_to_deg: float,
    current_speed_kn: float,
) -> DriftVectors:
    leeway_kmh = wind_speed_kn * LEEWAY_FACTOR * KNOT_TO_KMH
    blow_to = (wind_from_deg + 180.0) % 360.0
    leeway_east, leeway_north = velocity_components(blow_to, leeway_kmh)
    current_kmh = current_speed_kn * KNOT_TO_KMH
    current_east, current_north = velocity_components(current_to_deg, current_kmh)
    return DriftVectors(
        leeway_east_kmh=leeway_east,
        leeway_north_kmh=leeway_north,
        current_east_kmh=current_east,
        current_north_kmh=current_north,
        east_kmh=leeway_east + current_east,
        north_kmh=leeway_north + current_north,
        blow_to_deg=blow_to,
    )


def cone_radius_km(hours: float) -> float:
    return round(0.25 + 0.35 * hours, 3)


def cone_spread_deg(hours: float) -> float:
    return min(70.0, 12.0 + 6.0 * hours)


def sample_phase_deg(seed: int) -> float:
    return random.Random(seed).uniform(-0.25, 0.25)


def resolve_seed(seed: int | None) -> int:
    if seed is None:
        return int(os.getenv("SEASWARM_SEED", "42"))
    return seed


@dataclass(frozen=True)
class DriftCone:
    origin_lat: float
    origin_lon: float
    center_lat: float
    center_lon: float
    bearing_deg: float
    distance_km: float
    radius_km: float
    spread_deg: float
    east_km: float
    north_km: float
    heading_deg: float | None
    phase_deg: float
    polygon: tuple[tuple[float, float], ...]

    def to_dict(self) -> dict:
        return {
            "origin_lat": round(self.origin_lat, 5),
            "origin_lon": round(self.origin_lon, 5),
            "center_lat": round(self.center_lat, 5),
            "center_lon": round(self.center_lon, 5),
            "bearing_deg": round(self.bearing_deg, 2),
            "distance_km": round(self.distance_km, 3),
            "radius_km": self.radius_km,
            "spread_deg": self.spread_deg,
            "east_km": round(self.east_km, 3),
            "north_km": round(self.north_km, 3),
            "heading_deg": self.heading_deg,
            "polygon": [[lat, lon] for lat, lon in self.polygon],
        }


def drift_cone(
    *,
    lat: float,
    lon: float,
    hours: float,
    wind_from_deg: float,
    wind_speed_kn: float,
    current_to_deg: float,
    current_speed_kn: float,
    heading_deg: float | None = None,
    seed: int | None = None,
    arc_steps: int = 8,
) -> DriftCone:
    """Integrate leeway and current. `hours` is time since the last known position."""
    if hours < 0:
        raise ValueError("hours elapsed cannot be negative")
    vectors = drift_vectors(wind_from_deg, wind_speed_kn, current_to_deg, current_speed_kn)
    east = vectors.east_kmh * hours
    north = vectors.north_kmh * hours
    center_lat, center_lon = move_km(lat, lon, east, north)
    distance = math.hypot(east, north)
    if distance == 0:
        bearing = heading_deg if heading_deg is not None else 0.0
    else:
        bearing = math.degrees(math.atan2(east, north)) % 360.0
    radius = cone_radius_km(hours)
    spread = cone_spread_deg(hours)
    phase = sample_phase_deg(resolve_seed(seed))
    outer = distance + radius
    points: list[tuple[float, float]] = [(round(lat, 5), round(lon, 5))]
    steps = max(arc_steps, 1)
    for index in range(steps + 1):
        step_bearing = bearing - spread + phase + (2 * spread) * (index / steps)
        step_east, step_north = velocity_components(step_bearing, outer)
        point_lat, point_lon = move_km(lat, lon, step_east, step_north)
        points.append((round(point_lat, 5), round(point_lon, 5)))
    points.append(points[0])
    return DriftCone(
        origin_lat=lat,
        origin_lon=lon,
        center_lat=center_lat,
        center_lon=center_lon,
        bearing_deg=bearing,
        distance_km=distance,
        radius_km=radius,
        spread_deg=spread,
        east_km=east,
        north_km=north,
        heading_deg=heading_deg,
        phase_deg=phase,
        polygon=tuple(points),
    )
