"""Pinned operation checklist. Boxes follow stored rows, not the model's wording."""

from __future__ import annotations

from datetime import datetime


def render_ops_log(
    *,
    boat_name: str,
    operation,
    approvals: list,
    evidence_rows: list,
    events: list,
    sectors: list,
    followup_at: datetime,
    interval_minutes: int,
) -> str:
    counts = {"photo": 0, "gps": 0, "note": 0}
    for row in evidence_rows:
        counts[row.kind] = counts.get(row.kind, 0) + 1
    evidence_label = (
        f"Evidence recorded (photo {counts['photo']}, gps {counts['gps']}, note {counts['note']})"
    )
    lines = [
        f"## Operation {boat_name}",
        f"Status: {operation.status}",
        f"Opened by: {operation.opened_by}",
        "Checklist:",
        _box(_has(events, "drift_cone") or _has(events, "report"), "Situation report"),
        _box(bool(sectors), "Sectors assigned"),
        _box(_signed(approvals, "escalation"), "Escalation signed off"),
        _box(_signed(approvals, "scheme-outreach"), "Scheme outreach signed off"),
        _box(sum(counts.values()) > 0, evidence_label),
        _box(operation.status == "closed", "Search closed by a community_leader"),
        (
            f"Follow-up: next prompt at {followup_at.strftime('%H:%M')} "
            f"(every {interval_minutes} minutes)."
        ),
        "Humans decide. This log does not send anything outside the room.",
    ]
    return "\n".join(lines)


def _box(done: bool, label: str) -> str:
    mark = "x" if done else " "
    return f"- [{mark}] {label}"


def _has(events: list, kind: str) -> bool:
    return any(row.kind == kind for row in events)


def _signed(approvals: list, action_type: str) -> bool:
    rows = [row for row in approvals if row.action_type == action_type]
    return bool(rows) and rows[-1].status == "approved"
