"""Draft the escalation, match schemes, and release an action only after sign-off."""

from __future__ import annotations

from datetime import datetime

from agents.action_agent.commands import is_mention, wants_close
from agents.action_agent.draft import (
    escalation_payload,
    family_profile,
    render_escalation,
    render_schemes,
    scenario_day,
)
from agents.action_agent.evidence import parse_evidence
from agents.action_agent.followup import next_followup
from agents.action_agent.log import render_ops_log
from agents.common.db import init_db, session_scope
from agents.common.gate import (
    GateError,
    decide,
    parse_decision,
    perform_irreversible,
    request_approval,
)
from agents.common.llm import phrase
from agents.common.room import load_room
from agents.common.settings import get_settings
from agents.common.store import (
    add_evidence,
    find_open_operation,
    latest_approval,
    list_approvals,
    list_events,
    list_evidence,
    list_sectors,
    record_event,
    set_operation_status,
)
from core.load import load_json
from core.schemes_matcher import match_schemes


def handle_event(event: dict) -> str | list[str] | None:
    if event.get("username") == "action":
        return None
    text = (event.get("text") or "").strip()
    if not text or not _interesting(event, text):
        return None
    engine = init_db()
    with session_scope(engine) as session:
        return build_reply(session, event)


def build_reply(session, event: dict) -> str | list[str]:
    text = (event.get("text") or "").strip()
    actor = event.get("actor_type") or ""
    username = event.get("username") or "unknown"
    room = load_room()
    catalog = {boat["id"]: boat for boat in load_json("boats.json")["boats"]}
    boat = catalog.get(room["boat_id"])
    if boat is None:
        return f"The room boat {room['boat_id']} is not in the register."
    operation = find_open_operation(session, boat["id"])
    if operation is None:
        return "No open search is stored. Ask context for a situation report first."

    if actor == "human":
        decision = parse_decision(text)
        if decision is not None:
            action_type, approved = decision
            replies = release_signed(
                session,
                operation,
                action_type,
                username,
                event.get("message_id"),
                approved,
            )
            replies.append(_ops_log(session, operation, boat, room))
            return replies
        if text.lower().startswith("gps:"):
            line = parse_evidence(text)
            if line is None or not line.uri:
                return "That GPS line needs a latitude and longitude, for example gps: 17.8136, 73.0394"
        evidence = parse_evidence(text)
        if evidence is not None:
            return _record_evidence(session, operation, boat, room, evidence, username, event)
        if wants_close(text):
            return _request_close(session, operation, boat, room)

    if is_mention(text):
        return open_case(session, operation, boat, room)
    return "Say @action to draft the escalation, or post a photo, a gps fix, or a sign-off."


def open_case(session, operation, boat: dict, room: dict) -> list[str]:
    """Create pending cards. This function does not release anything."""
    payload = escalation_payload(boat, room)
    escalation = _ensure_pending(session, operation.id, "escalation", payload)
    profile = family_profile(boat, room)
    matches = match_schemes(
        profile,
        load_json("schemes.json")["schemes"],
        today=scenario_day(room),
    )
    scheme_payload = {
        "eligible": [match.scheme_id for match in matches if match.eligible],
        "family_rep": boat.get("family_rep") or "",
    }
    scheme = _ensure_pending(session, operation.id, "scheme-outreach", scheme_payload)
    card = render_escalation(boat, payload, escalation)
    schemes = render_schemes(boat["name"], matches, scheme)
    card = phrase(
        agent="action",
        facts={"escalation": payload, "status": getattr(escalation, "status", "missing")},
        fallback=card,
        required=_card_required(boat, payload, card),
    )
    schemes = phrase(
        agent="action",
        facts={"schemes": [match.scheme_id for match in matches]},
        fallback=schemes,
        required=_scheme_required(matches, schemes),
    )
    return [card, schemes, _ops_log(session, operation, boat, room)]


def release_signed(
    session,
    operation,
    action_type: str,
    username: str,
    message_id: str | None,
    approved: bool,
) -> list[str]:
    """Apply a human sign-off. The status change runs only after the gate allows it."""
    result = decide(
        session,
        op_id=operation.id,
        action_type=action_type,
        username=username,
        message_id=message_id,
        approved=approved,
    )
    replies = [result.reply]
    if result.ok and approved and result.approval is not None:
        try:
            replies.append(perform_irreversible(session, result.approval.id))
        except GateError as exc:
            replies.append(str(exc))
            return replies
        if action_type == "close-operation":
            set_operation_status(session, operation.id, "closed")
            record_event(
                session,
                op_id=operation.id,
                actor=username,
                actor_type="human",
                kind="operation_closed",
                body="closed",
                message_id=message_id,
            )
    return replies


def _request_close(session, operation, boat: dict, room: dict) -> list[str]:
    approval = _ensure_pending(
        session,
        operation.id,
        "close-operation",
        {"boat": boat["name"]},
    )
    if approval is not None and approval.status == "approved":
        note = "The search is already closed."
    elif approval is None:
        note = (
            "The close request was not stored. Persistence is off, so this sign-off will be lost."
        )
    else:
        note = (
            "PENDING approval — close-operation\n"
            "A community_leader replies:\n"
            "Approved — close-operation"
        )
    return [note, _ops_log(session, operation, boat, room)]


def _record_evidence(
    session, operation, boat, room, evidence, username: str, event: dict
) -> list[str]:
    stored = add_evidence(
        session,
        op_id=operation.id,
        kind=evidence.kind,
        uri=evidence.uri,
        submitted_by=username,
    )
    if stored is None:
        return [
            f"Evidence was not stored. Persistence is off, so this {evidence.kind} is lost.",
            _ops_log(session, operation, boat, room),
        ]
    record_event(
        session,
        op_id=operation.id,
        actor=username,
        actor_type="human",
        kind="evidence",
        body=f"{evidence.kind}:{evidence.uri}",
        message_id=event.get("message_id"),
    )
    return [
        f"Recorded {evidence.kind} from {username}: {evidence.uri}",
        _ops_log(session, operation, boat, room),
    ]


def _ensure_pending(session, op_id: int, action_type: str, payload: dict):
    latest = latest_approval(session, op_id, action_type)
    if latest is not None and latest.status in {"pending", "approved"}:
        return latest
    return request_approval(
        session,
        op_id=op_id,
        action_type=action_type,
        payload=payload,
        requested_by_agent="action",
    )


def _ops_log(session, operation, boat: dict, room: dict) -> str:
    interval = get_settings().followup_interval_seconds
    start = datetime.fromisoformat(room["scenario_now"])
    return render_ops_log(
        boat_name=boat["name"],
        operation=operation,
        approvals=list_approvals(session, operation.id),
        evidence_rows=list_evidence(session, operation.id),
        events=list_events(session, operation.id),
        sectors=list_sectors(session, operation.id),
        followup_at=next_followup(start, interval),
        interval_minutes=max(1, interval // 60),
    )


def _interesting(event: dict, text: str) -> bool:
    actor = event.get("actor_type") or ""
    if actor == "human" and (
        parse_decision(text) is not None or parse_evidence(text) is not None or wants_close(text)
    ):
        return True
    if actor == "human" and text.lower().startswith("gps:"):
        return True
    return is_mention(text)


def _card_required(boat: dict, payload: dict, card: str) -> list[str]:
    required = [boat["name"], boat["licence_no"], f"{payload['overdue_hours']:.1f}"]
    if "Approved — escalation" in card:
        required.append("Approved — escalation")
    if "NOT STORED" in card:
        required.append("NOT STORED")
    if "PENDING" in card:
        required.append("PENDING")
    if "APPROVED" in card:
        required.append("APPROVED")
    return required


def _scheme_required(matches, schemes: str) -> list[str]:
    required: list[str] = []
    for match in matches:
        if match.eligible:
            required.append(str(match.amount_inr))
            required.append(match.deadline.isoformat())
        elif match.reasons:
            required.append("not eligible")
    if "Approved — scheme-outreach" in schemes:
        required.append("Approved — scheme-outreach")
    return required
