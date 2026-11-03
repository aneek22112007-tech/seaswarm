"""Build the situation report and hand the room to @options."""

from __future__ import annotations

import json
from datetime import datetime

from agents.common.db import init_db, session_scope
from agents.common.llm import phrase
from agents.common.room import load_room
from agents.common.store import (
    create_operation,
    ensure_boat,
    find_open_operation,
    latest_position,
    list_events,
    persistence_enabled,
    record_event,
)
from agents.context_agent.parse import (
    boat_from_text,
    is_trigger,
    parse_daylight_hours,
    parse_overdue_hours,
)
from agents.context_agent.summary import render_summary, required_figures
from core.drift import drift_cone
from core.load import load_json


def handle_event(event: dict) -> str | None:
    if event.get("actor_type") != "human":
        return None
    text = event.get("text") or ""
    if not is_trigger(text):
        return None
    engine = init_db()
    with session_scope(engine) as session:
        return build_reply(session, event)


def build_reply(session, event: dict) -> str:
    text = event.get("text") or ""
    username = event.get("username") or "unknown"
    room = load_room()
    catalog = load_json("boats.json")["boats"]
    history = _history(session, room["boat_id"])
    blob = text if not persistence_enabled() else "\n".join([text, *history])
    boat = boat_from_text(blob, catalog)
    if boat is None:
        return (
            "I could not find the boat in the room history or the register. "
            "Name the boat, for example Sagar-4."
        )
    ensure_boat(session, boat)
    operation = find_open_operation(session, boat["id"])
    if operation is None:
        operation = create_operation(session, boat_id=boat["id"], opened_by=username)
    if operation is not None:
        record_event(
            session,
            op_id=operation.id,
            actor=username,
            actor_type="human",
            kind="report",
            body=text,
            message_id=event.get("message_id"),
        )
    position = _position(session, boat["id"], room)
    weather = load_json("weather.json")
    tide = load_json("tide.json")
    overdue = parse_overdue_hours(text) or float(room["overdue_hours"])
    daylight = parse_daylight_hours(text) or float(room["daylight_hours_left"])
    cone = drift_cone(
        lat=position["lat"],
        lon=position["lon"],
        hours=overdue,
        wind_from_deg=weather["wind_from_deg"],
        wind_speed_kn=weather["wind_speed_kn"],
        current_to_deg=tide["current_to_deg"],
        current_speed_kn=tide["current_speed_kn"],
        heading_deg=float(room["heading_deg"]),
    )
    facts = _facts(
        boat=boat,
        position=position,
        cone=cone,
        weather=weather,
        tide=tide,
        overdue=overdue,
        daylight=daylight,
        opened_by=operation.opened_by if operation is not None else username,
        heading=float(room["heading_deg"]),
    )
    if operation is not None:
        record_event(
            session,
            op_id=operation.id,
            actor="context",
            actor_type="agent",
            kind="drift_cone",
            body=json.dumps(cone.to_dict()),
            message_id=event.get("message_id"),
        )
    fallback = render_summary(facts)
    return phrase(
        agent="context",
        facts=facts,
        fallback=fallback,
        required=required_figures(facts),
    )


def _history(session, boat_id: str) -> list[str]:
    operation = find_open_operation(session, boat_id)
    if operation is None:
        return []
    return [row.body for row in list_events(session, operation.id)]


def _position(session, boat_id: str, room: dict) -> dict:
    stored = latest_position(session, boat_id)
    if stored is not None:
        return {
            "lat": stored.lat,
            "lon": stored.lon,
            "source": stored.source,
            "reported_at": stored.reported_at.isoformat(),
        }
    fallback = room["last_known"]
    if boat_id == room["boat_id"]:
        return {
            "lat": float(fallback["lat"]),
            "lon": float(fallback["lon"]),
            "source": fallback["source"],
            "reported_at": fallback["reported_at"],
        }
    return {"lat": 0.0, "lon": 0.0, "source": "unknown", "reported_at": ""}


def _facts(*, boat, position, cone, weather, tide, overdue, daylight, opened_by, heading) -> dict:
    crew = boat.get("crew") or []
    return {
        "boat_name": boat["name"],
        "owner": boat["owner"],
        "licence_no": boat["licence_no"],
        "crew_names": [person["name"] for person in crew],
        "crew_count": len(crew),
        "opened_by": opened_by,
        "overdue_hours": overdue,
        "daylight_hours": daylight,
        "heading_deg": heading,
        "lat": position["lat"],
        "lon": position["lon"],
        "source": position["source"],
        "center_lat": cone.center_lat,
        "center_lon": cone.center_lon,
        "bearing_deg": cone.bearing_deg,
        "distance_km": cone.distance_km,
        "radius_km": cone.radius_km,
        "spread_deg": cone.spread_deg,
        "wind_speed_kn": weather["wind_speed_kn"],
        "wind_from_deg": weather["wind_from_deg"],
        "sea_state": weather["sea_state"],
        "wave_height_m": weather["wave_height_m"],
        "tide_state": tide["tide_state"],
        "current_speed_kn": tide["current_speed_kn"],
        "current_to_deg": tide["current_to_deg"],
        "reported_at": position["reported_at"],
        "computed_at": datetime.now().isoformat(),
    }
