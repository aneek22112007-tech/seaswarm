"""Human gate. A gated action runs only after an approved row exists.

`request_approval` stores a pending card. `decide` records the person, role,
message id, and time. `perform_irreversible` is the only release path, and it
calls `execute_gated` before any side effect.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from agents.common.models import Approval, Event, utcnow
from agents.common.roles import role_for
from agents.common.store import (
    find_pending_approval,
    list_events,
    record_event,
    save_approval,
)

ACTION_ROLES = {
    "escalation": ("community_leader",),
    "spend": ("community_leader",),
    "external-message": ("community_leader",),
    "scheme-outreach": ("community_leader", "family_rep"),
    "close-operation": ("community_leader",),
}

APPROVAL_RE = re.compile(r"^Approved\s+—\s+(.+?)\s*$")
REJECTION_RE = re.compile(r"^Rejected\s+—\s+(.+?)\s*$")
ALIASES = {
    "escalation": "escalation",
    "escalate": "escalation",
    "spend": "spend",
    "external-message": "external-message",
    "external message": "external-message",
    "scheme-outreach": "scheme-outreach",
    "close-operation": "close-operation",
    "close": "close-operation",
}


class GateError(PermissionError):
    """Raised when code tries to release an action that has no approved row."""


@dataclass
class Decision:
    ok: bool
    reply: str
    approval: Approval | None = None


def normalize_action(raw: str) -> str:
    key = raw.strip().lower()
    return ALIASES.get(key, key)


def parse_decision(text: str) -> tuple[str, bool] | None:
    stripped = text.strip()
    approved = APPROVAL_RE.match(stripped)
    if approved:
        return normalize_action(approved.group(1)), True
    rejected = REJECTION_RE.match(stripped)
    if rejected:
        return normalize_action(rejected.group(1)), False
    return None


def denial_message(action_type: str) -> str:
    if action_type == "escalation":
        return "Only community_leader can approve escalation."
    roles = " or ".join(ACTION_ROLES.get(action_type, ("community_leader",)))
    return f"Only {roles} can approve {action_type}."


def request_approval(
    session,
    *,
    op_id: int,
    action_type: str,
    payload: dict,
    requested_by_agent: str,
) -> Approval | None:
    row = Approval(
        op_id=op_id,
        action_type=action_type,
        payload_json=json.dumps(payload),
        requested_by_agent=requested_by_agent,
        status="pending",
    )
    saved = save_approval(session, row)
    if saved is None:
        return None
    record_event(
        session,
        op_id=op_id,
        actor=requested_by_agent,
        actor_type="agent",
        kind="approval_requested",
        body=action_type,
    )
    return saved


def decide(
    session,
    *,
    op_id: int,
    action_type: str,
    username: str,
    message_id: str | None,
    approved: bool,
) -> Decision:
    pending = find_pending_approval(session, op_id, action_type)
    if pending is None:
        return Decision(
            ok=False,
            reply=f"No pending approval for {action_type}. The sign-off was not applied.",
        )
    role = role_for(username)
    if role not in ACTION_ROLES.get(action_type, ()):
        record_event(
            session,
            op_id=op_id,
            actor=username,
            actor_type="human",
            kind="approval_denied",
            body=denial_message(action_type),
            message_id=message_id,
        )
        return Decision(ok=False, reply=denial_message(action_type), approval=pending)
    pending.status = "approved" if approved else "rejected"
    pending.approver = username
    pending.approver_role = role
    pending.message_id = message_id
    pending.decided_at = utcnow()
    verb = "approved" if approved else "rejected"
    record_event(
        session,
        op_id=op_id,
        actor=username,
        actor_type="human",
        kind="approval_decided",
        body=f"{verb} {action_type}",
        message_id=message_id,
    )
    return Decision(
        ok=True,
        reply=f"{username} ({role}) {verb} {action_type}.",
        approval=pending,
    )


def execute_gated(session, approval_id: int) -> Event:
    approval = session.get(Approval, approval_id)
    if approval is None or approval.status != "approved":
        raise GateError("refusing irreversible action without an approved row")
    for existing in list_events(session, approval.op_id, kind="gated_executed"):
        if f"approval:{approval.id}" in existing.body:
            raise GateError("action already executed")
    recorded = record_event(
        session,
        op_id=approval.op_id,
        actor=approval.approver or "unknown",
        actor_type="human",
        kind="gated_executed",
        body=f"approval:{approval.id} {approval.action_type}",
        message_id=approval.message_id,
    )
    if recorded is None:
        raise GateError("refusing irreversible action without an approved row")
    return recorded


def perform_irreversible(session, approval_id: int) -> str:
    """Release a signed-off action. Nothing is released if execute_gated refuses."""
    event = execute_gated(session, approval_id)
    return f"Released {event.body} into the audit trail."
