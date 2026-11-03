"""Escalation card and scheme note. Amounts and deadlines come from core/."""

from __future__ import annotations

from datetime import date, datetime

from core.schemes_matcher import SchemeMatch


def escalation_payload(boat: dict, room: dict) -> dict:
    last = room["last_known"]
    crew = [person["name"] for person in boat.get("crew") or []]
    return {
        "to": "Coast Guard / marine police, Harnai",
        "boat": boat["name"],
        "licence_no": boat["licence_no"],
        "district": boat["district"],
        "home_port": boat["home_port"],
        "crew": crew,
        "overdue_hours": float(room["overdue_hours"]),
        "last_known": {"lat": float(last["lat"]), "lon": float(last["lon"])},
    }


def family_profile(boat: dict, room: dict) -> dict:
    return {
        "district": boat["district"],
        "licence_no": boat["licence_no"],
        "overdue_hours": float(room["overdue_hours"]),
        "gear": boat.get("gear") or "",
        "crew_count": len(boat.get("crew") or []),
        "home_port": boat["home_port"],
    }


def scenario_day(room: dict) -> date:
    return datetime.fromisoformat(room["scenario_now"]).date()


def render_escalation(boat: dict, payload: dict, approval) -> str:
    crew = ", ".join(payload["crew"])
    position = payload["last_known"]
    header, footer = _escalation_state(approval)
    return (
        f"{header}\n"
        f"To: {payload['to']}\n"
        f"Boat: {boat['name']} ({boat['licence_no']}), {boat['home_port']}, {boat['district']}\n"
        f"Crew: {crew}\n"
        f"Overdue: {payload['overdue_hours']:.1f} h\n"
        f"Last known: {position['lat']}, {position['lon']}\n"
        f"{footer}"
    )


def render_schemes(boat_name: str, matches: list[SchemeMatch], approval) -> str:
    lines = [f"Scheme matches for the family of {boat_name} (computed, not guessed):"]
    for match in matches:
        documents = ", ".join(match.documents) if match.documents else "none"
        if match.eligible:
            lines.append(
                f"- {match.name}: eligible, INR {match.amount_inr}, "
                f"deadline {match.deadline.isoformat()}, documents: {documents}"
            )
        else:
            reason = match.reasons[0] if match.reasons else "rules did not match"
            lines.append(f"- {match.name}: not eligible ({reason})")
    if approval is not None and approval.status == "approved":
        lines.append(
            f"Scheme outreach was signed by {approval.approver} ({approval.approver_role})."
        )
    else:
        lines.append(
            "Sending the packet outside the room waits for a sign-off:\n"
            "Approved — scheme-outreach"
        )
    return "\n".join(lines)


def _escalation_state(approval) -> tuple[str, str]:
    if approval is None:
        return (
            "NOT STORED — escalation",
            "Persistence is off, so this sign-off will be lost.",
        )
    if approval.status == "approved":
        return (
            f"APPROVED by {approval.approver} ({approval.approver_role}) — escalation",
            "The sign-off is in the audit trail.",
        )
    if approval.status == "rejected":
        return (
            f"REJECTED by {approval.approver} — escalation",
            "A community_leader can ask for a new draft by mentioning @action.",
        )
    return (
        "PENDING approval — escalation",
        "This draft stays in the room until a community_leader replies:\nApproved — escalation",
    )
