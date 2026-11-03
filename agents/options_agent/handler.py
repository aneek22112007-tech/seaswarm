"""Re-plan when the room asks, and say a sector conflict out loud."""

from __future__ import annotations

from agents.common.db import init_db, session_scope
from agents.common.llm import phrase
from agents.common.room import load_room
from agents.common.store import find_open_operation, list_sectors
from agents.options_agent.commands import parse_command
from agents.options_agent.planner import (
    apply_command,
    cone_for,
    ensure_sector_rows,
    make_options,
    render_plan,
)
from core.load import load_json


def handle_event(event: dict) -> str | None:
    if event.get("username") == "options":
        return None
    command = parse_command(event.get("text") or "", event.get("actor_type") or "")
    if command is None:
        return None
    engine = init_db()
    with session_scope(engine) as session:
        return build_reply(session, command)


def build_reply(session, command) -> str:
    room = load_room()
    boat_id = room["boat_id"]
    catalog = {boat["id"]: boat for boat in load_json("boats.json")["boats"]}
    boat_name = catalog[boat_id]["name"]
    operation = find_open_operation(session, boat_id)
    if operation is None:
        return (
            "No open search is stored, so I cannot assign sectors. "
            "Ask context for a situation report first."
        )
    ensure_sector_rows(session, operation.id, cone_for(session, operation.id, room))
    conflict = apply_command(session, operation.id, command)
    if conflict:
        return phrase(
            agent="options",
            facts={"conflict": conflict},
            fallback=conflict,
            required=[conflict],
        )
    rows = list_sectors(session, operation.id)
    if rows and all(row.status == "clear" for row in rows):
        return (
            "All sectors are clear. I will not close the search. "
            "A community_leader has to sign off before it is closed.\n@action"
        )
    options = make_options(session, operation.id)
    assignments = [
        f"{row.name}={row.assigned_boat or row.status}"
        for row in list_sectors(session, operation.id)
    ]
    # Persistence off hides rows from list_sectors, so show the latest inserted names
    # only when the read path can see them. The message still carries three options.
    fallback = render_plan(boat_name, options, assignments)
    required = [f"Option {option.option_id}" for option in options]
    required.append(f"{options[0].coverage_pct:.1f}")
    required.append("@action")
    facts = {
        "options": [
            {
                "id": option.option_id,
                "coverage_pct": option.coverage_pct,
                "fuel_litres": option.fuel_litres,
                "cost_inr": option.cost_inr,
            }
            for option in options
        ]
    }
    return phrase(agent="options", facts=facts, fallback=fallback, required=required)
