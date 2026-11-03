"""Turn a drift cone into three options and keep sector rows honest."""

from __future__ import annotations

import json

from agents.common.models import utcnow
from agents.common.room import load_room
from agents.common.store import insert_sector, list_events, list_sectors, record_event
from agents.options_agent.commands import Command
from core.conflicts import assignment_conflict
from core.drift import DriftCone, drift_cone
from core.load import load_json
from core.plans import SearchOption, build_options
from core.sectors import split_sectors


def cone_for(session, op_id: int, room: dict) -> DriftCone:
    stored = list_events(session, op_id, kind="drift_cone")
    if stored:
        return _cone_from_dict(json.loads(stored[-1].body))
    weather = load_json("weather.json")
    tide = load_json("tide.json")
    last = room["last_known"]
    return drift_cone(
        lat=float(last["lat"]),
        lon=float(last["lon"]),
        hours=float(room["overdue_hours"]),
        wind_from_deg=weather["wind_from_deg"],
        wind_speed_kn=weather["wind_speed_kn"],
        current_to_deg=tide["current_to_deg"],
        current_speed_kn=tide["current_speed_kn"],
        heading_deg=float(room["heading_deg"]),
    )


def ensure_sector_rows(session, op_id: int, cone: DriftCone) -> list:
    """Insert any missing sector names. A second call with persistence on does not duplicate."""
    existing = {row.name: row for row in list_sectors(session, op_id)}
    for sector in split_sectors(cone, count=3):
        if sector.name in existing:
            continue
        existing[sector.name] = insert_sector(
            session,
            op_id=op_id,
            name=sector.name,
            polygon_json=json.dumps(sector.polygon),
            status="unassigned",
            assigned_boat=None,
            updated_at=utcnow(),
        )
    return list(existing.values())


def rejected_options(session, op_id: int) -> set[str]:
    return {row.body for row in list_events(session, op_id, kind="option_rejected")}


def apply_command(session, op_id: int, command: Command) -> str | None:
    """Apply a human correction. A conflict string means the assignment was refused."""
    if command.kind == "reject" and command.option_id:
        record_event(
            session,
            op_id=op_id,
            actor="options",
            actor_type="agent",
            kind="option_rejected",
            body=command.option_id,
        )
        return None
    if command.kind == "clear" and command.sector:
        sector = _named(session, op_id, command.sector)
        if sector is None:
            return f"No sector named {command.sector}."
        sector.status = "clear"
        sector.updated_at = utcnow()
        record_event(
            session,
            op_id=op_id,
            actor="options",
            actor_type="agent",
            kind="sector_clear",
            body=command.sector,
        )
        return None
    if command.kind == "reassign" and command.sector and command.boat:
        existing = {row.name: row.assigned_boat for row in list_sectors(session, op_id)}
        conflict = assignment_conflict(existing, command.sector, command.boat)
        if conflict:
            record_event(
                session,
                op_id=op_id,
                actor="options",
                actor_type="agent",
                kind="conflict",
                body=conflict,
            )
            return conflict
        sector = _named(session, op_id, command.sector)
        if sector is None:
            insert_sector(
                session,
                op_id=op_id,
                name=command.sector,
                polygon_json="[]",
                status="assigned",
                assigned_boat=command.boat,
                updated_at=utcnow(),
            )
        else:
            sector.assigned_boat = command.boat
            sector.status = "assigned"
            sector.updated_at = utcnow()
        record_event(
            session,
            op_id=op_id,
            actor="options",
            actor_type="agent",
            kind="reassign",
            body=f"{command.boat} {command.sector}",
        )
    return None


def make_options(session, op_id: int) -> list[SearchOption]:
    room = load_room()
    cone = cone_for(session, op_id, room)
    ensure_sector_rows(session, op_id, cone)
    weather = load_json("weather.json")
    active = [sector for sector in split_sectors(cone, count=3)]
    clear_names = {row.name for row in list_sectors(session, op_id) if row.status == "clear"}
    # list_sectors is empty when persistence is off, so clear_names stays empty and
    # ensure_sector_rows inserts a fresh copy on every call.
    if clear_names:
        active = [sector for sector in active if sector.name not in clear_names] or active
    return build_options(
        sectors=active,
        boats=list(room["search_boats"]),
        rejected=rejected_options(session, op_id),
        wave_height_m=weather["wave_height_m"],
        wind_speed_kn=weather["wind_speed_kn"],
        sea_state=weather["sea_state"],
        rough_after=room["rough_after"],
        start_hhmm=room["scenario_hhmm"],
        daylight_hours_left=float(room["daylight_hours_left"]),
    )


def render_plan(boat_name: str, options: list[SearchOption], assignments: list[str]) -> str:
    lines = [f"Three options for {boat_name}"]
    if assignments:
        lines.append("Assignments: " + "; ".join(assignments))
    for option in options:
        flags = "; ".join(option.risk_flags) if option.risk_flags else "none"
        lines.extend(
            [
                "",
                f"Option {option.option_id} — {option.title}",
                f"Boats: {', '.join(option.boats)}",
                f"Sectors: {', '.join(option.sector_names)}",
                f"Coverage: {option.coverage_pct:.1f}%",
                f"Estimated time: {option.estimated_hours:.2f} h",
                f"Fuel: {option.fuel_litres:.1f} L",
                f"Cost: INR {option.cost_inr:.2f}",
                f"Daylight margin: {option.daylight_margin_hours:.2f} h",
                f"Risks: {flags}",
            ]
        )
    lines.append("")
    lines.append('Reply "reject option B", "Sector-1 clear", or "reassign Meerabai to Sector-1".')
    lines.append("@action")
    return "\n".join(lines)


def _named(session, op_id: int, name: str):
    for sector in list_sectors(session, op_id):
        if sector.name == name:
            return sector
    return None


def _cone_from_dict(data: dict) -> DriftCone:
    polygon = tuple((point[0], point[1]) for point in data["polygon"])
    return DriftCone(
        origin_lat=data["origin_lat"],
        origin_lon=data["origin_lon"],
        center_lat=data["center_lat"],
        center_lon=data["center_lon"],
        bearing_deg=data["bearing_deg"],
        distance_km=data["distance_km"],
        radius_km=data["radius_km"],
        spread_deg=data["spread_deg"],
        east_km=data["east_km"],
        north_km=data["north_km"],
        heading_deg=data.get("heading_deg"),
        phase_deg=0.0,
        polygon=polygon,
    )
