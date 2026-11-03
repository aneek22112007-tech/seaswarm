"""Risk flags from weather, the clock, and the daylight margin.

Times are same-day `HH:MM` strings. The rough-sea flag uses the clock in the
mock, so the demo can say "rough seas after 16:30, recommend against".
"""

from __future__ import annotations


def add_hours(hhmm: str, hours: float) -> str:
    hour_text, minute_text = hhmm.split(":")
    total = int(hour_text) * 60 + int(minute_text) + int(round(hours * 60))
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def risk_flags(
    *,
    wave_height_m: float,
    wind_speed_kn: float,
    sea_state: int,
    rough_after: str,
    start_hhmm: str,
    estimated_hours: float,
    daylight_margin_hours: float,
) -> list[str]:
    flags: list[str] = []
    finished_at = add_hours(start_hhmm, estimated_hours)
    rough = (wave_height_m >= 1.2 or sea_state >= 4) and finished_at > rough_after
    if rough:
        flags.append(f"rough seas after {rough_after}, recommend against")
    if daylight_margin_hours < 0.5:
        flags.append("daylight margin under 30 minutes")
    if wind_speed_kn >= 20:
        flags.append("wind at or above 20 kn")
    if wave_height_m >= 2.0:
        flags.append("wave height at or above 2.0 m")
    return flags
