"""One-screen situation report. Every figure is passed in already computed."""

from __future__ import annotations


def render_summary(facts: dict) -> str:
    crew = ", ".join(facts["crew_names"])
    return "\n".join(
        [
            f"{facts['boat_name']} — overdue search",
            (
                f"Who: {crew} ({facts['crew_count']} crew), owner {facts['owner']}, "
                f"licence {facts['licence_no']}"
            ),
            (f"Since: overdue {facts['overdue_hours']:.1f} h, " f"opened by {facts['opened_by']}"),
            (
                f"Heading: {facts['heading_deg']:.0f}° from last known "
                f"{facts['lat']:.5f}, {facts['lon']:.5f} ({facts['source']})"
            ),
            (
                f"Drift cone: center {facts['center_lat']:.5f}, {facts['center_lon']:.5f}, "
                f"bearing {facts['bearing_deg']:.0f}°, distance {facts['distance_km']:.1f} km, "
                f"radius {facts['radius_km']:.2f} km, spread {facts['spread_deg']:.0f}°"
            ),
            f"Daylight left: {facts['daylight_hours']:.1f} h",
            (
                f"Wind: {facts['wind_speed_kn']:.0f} kn from {facts['wind_from_deg']:.0f}°. "
                f"Sea state {facts['sea_state']}, waves {facts['wave_height_m']:.1f} m. "
                f"Tide: {facts['tide_state']}, current {facts['current_speed_kn']:.1f} kn "
                f"toward {facts['current_to_deg']:.0f}°."
            ),
            "@options",
        ]
    )


def required_figures(facts: dict) -> list[str]:
    return [
        facts["boat_name"],
        f"{facts['radius_km']:.2f}",
        f"{facts['daylight_hours']:.1f}",
        "@options",
    ]
