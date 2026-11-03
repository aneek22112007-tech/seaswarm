"""Three search options. Rejecting one swaps that strategy and still returns three."""

from __future__ import annotations

from dataclasses import dataclass

from core.cost import cost_inr, coverage_pct, estimate_hours, fuel_litres
from core.daylight import daylight_margin
from core.risk import risk_flags
from core.sectors import SectorSlice


@dataclass(frozen=True)
class SearchOption:
    option_id: str
    title: str
    boats: tuple[str, ...]
    sector_names: tuple[str, ...]
    coverage_pct: float
    estimated_hours: float
    fuel_litres: float
    cost_inr: float
    daylight_margin_hours: float
    risk_flags: tuple[str, ...]


def build_options(
    *,
    sectors: list[SectorSlice],
    boats: list[str],
    rejected: set[str] | None = None,
    wave_height_m: float,
    wind_speed_kn: float,
    sea_state: int,
    rough_after: str,
    start_hhmm: str,
    daylight_hours_left: float,
) -> list[SearchOption]:
    if len(sectors) < 1:
        raise ValueError("options need sectors")
    refused = {item.upper() for item in (rejected or set())}
    ranked = sorted(sectors, key=lambda sector: (-sector.probability, sector.name))
    boat_names = list(boats)
    strategies: list[tuple] = [
        ("A", "one boat on the highest sector", boat_names[:1], ranked[:1], 1.0),
        ("B", "two boats on the two highest sectors", boat_names[:2], ranked[:2], 1.2),
        ("C", "three boats across all sectors", boat_names[:3], list(sectors), 1.5),
    ]
    if "B" in refused:
        strategies[1] = (
            "B",
            "revised: one boat sweeping two sectors in sequence",
            boat_names[:1],
            ranked[:2],
            2.4,
        )
    options: list[SearchOption] = []
    for option_id, title, chosen_boats, chosen_sectors, search_hours in strategies:
        if not chosen_boats:
            chosen_boats = ["unassigned"]
        if not chosen_sectors:
            chosen_sectors = ranked[:1]
        transit = max(sector.mid_km for sector in chosen_sectors)
        angle = sum(sector.angle_deg for sector in chosen_sectors)
        outer = max(sector.outer_km for sector in chosen_sectors)
        hours = estimate_hours(transit, search_hours)
        litres = fuel_litres(transit, search_hours, len(chosen_boats))
        margin = daylight_margin(daylight_hours_left, hours)
        flags = risk_flags(
            wave_height_m=wave_height_m,
            wind_speed_kn=wind_speed_kn,
            sea_state=sea_state,
            rough_after=rough_after,
            start_hhmm=start_hhmm,
            estimated_hours=hours,
            daylight_margin_hours=margin,
        )
        options.append(
            SearchOption(
                option_id=option_id,
                title=title,
                boats=tuple(chosen_boats),
                sector_names=tuple(sector.name for sector in chosen_sectors),
                coverage_pct=coverage_pct(outer, angle, len(chosen_boats), search_hours),
                estimated_hours=hours,
                fuel_litres=litres,
                cost_inr=cost_inr(litres),
                daylight_margin_hours=margin,
                risk_flags=tuple(flags),
            )
        )
    if len(options) != 3:
        raise RuntimeError("the planner must return exactly three options")
    return options
