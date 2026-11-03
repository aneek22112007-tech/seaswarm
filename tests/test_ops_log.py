"""The pinned checklist reflects stored sign-offs and the scenario clock."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from agents.action_agent.log import render_ops_log


def test_checklist_marks_only_what_is_stored():
    operation = SimpleNamespace(status="searching", opened_by="ramesh")
    approvals = [SimpleNamespace(action_type="escalation", status="pending")]
    evidence = [SimpleNamespace(kind="photo")]
    events = [SimpleNamespace(kind="drift_cone")]
    followup_at = datetime(2026, 1, 15, 15, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    text = render_ops_log(
        boat_name="Sagar-4",
        operation=operation,
        approvals=approvals,
        evidence_rows=evidence,
        events=events,
        sectors=[],
        followup_at=followup_at,
        interval_minutes=30,
    )
    assert text.startswith("## Operation Sagar-4")
    assert "- [x] Situation report" in text
    assert "- [ ] Sectors assigned" in text
    assert "- [ ] Escalation signed off" in text
    assert "- [x] Evidence recorded (photo 1, gps 0, note 0)" in text
    assert "next prompt at 15:00" in text
    assert "every 30 minutes" in text
    assert "Humans decide." in text
