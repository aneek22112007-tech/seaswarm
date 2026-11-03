"""The audit names every actor, assignment, correction, and sign-off."""

from __future__ import annotations

from datetime import datetime, timezone

from agents.action_agent.handler import handle_event
from agents.common.audit import export_audit, render_audit
from agents.common.db import init_db, session_scope
from agents.common.models import Approval, Evidence, Sector, utcnow
from agents.common.store import record_event
from tests.factories import add_boat, add_operation

WHEN = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)


def _seed(session):
    add_boat(session)
    operation = add_operation(session, opened_by="ramesh")
    session.add(
        Sector(
            op_id=operation.id,
            name="Sector-1",
            polygon_json="[]",
            status="assigned",
            assigned_boat="Meerabai",
            updated_at=utcnow(),
        )
    )
    session.add(
        Approval(
            op_id=operation.id,
            action_type="escalation",
            payload_json="{}",
            requested_by_agent="action",
            status="approved",
            approver="ramesh",
            approver_role="community_leader",
            message_id="m-ramesh",
            decided_at=WHEN,
        )
    )
    session.add(
        Evidence(
            op_id=operation.id,
            kind="photo",
            uri="reef.jpg",
            submitted_by="sunita",
            created_at=WHEN,
        )
    )
    record_event(
        session,
        op_id=operation.id,
        actor="sunita",
        actor_type="human",
        kind="approval_denied",
        body="Only community_leader can approve escalation.",
        message_id="m-sunita",
        created_at=WHEN,
    )
    record_event(
        session,
        op_id=operation.id,
        actor="ramesh",
        actor_type="human",
        kind="approval_decided",
        body="approved escalation",
        message_id="m-ramesh",
        created_at=WHEN,
    )
    session.flush()
    return operation


def test_markdown_lists_the_signoff_the_denial_and_the_assignment(session):
    operation = _seed(session)
    text = render_audit(session, generated_at=WHEN)
    assert f"## Operation {operation.id} - Sagar-4" in text
    assert "Opened by: ramesh" in text
    assert "Meerabai" in text
    assert "community_leader" in text
    assert "m-ramesh" in text
    assert "sunita" in text
    assert "reef.jpg" in text
    assert "Only community_leader can approve escalation." in text
    assert "approved escalation" in text


def test_export_writes_markdown_and_a_pdf_that_contains_the_boat(session, tmp_path):
    _seed(session)
    exported = export_audit(
        session,
        tmp_path,
        actor="ramesh",
        actor_type="human",
        now=WHEN,
    )
    markdown = exported.markdown_path.read_text(encoding="utf-8")
    pdf = exported.pdf_path.read_bytes()
    assert exported.markdown_path.name == "audit-20260115T100000Z.md"
    assert "audit_exported" in markdown
    assert "ramesh" in markdown
    assert exported.event_count >= 3
    assert exported.signoff_count == 1
    assert pdf.startswith(b"%PDF")
    assert b"Sagar-4" in pdf
    assert b"Meerabai" in pdf
    assert b"community_leader" in pdf


def test_room_audit_command_writes_both_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'audit.db'}")
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("PERSISTENCE", "on")
    engine = init_db()
    with session_scope(engine) as session:
        _seed(session)
    reply = handle_event(
        {"actor_type": "human", "username": "ramesh", "text": "/audit", "message_id": "m-audit"}
    )
    assert isinstance(reply, str)
    assert "audit-20" in reply
    assert ".md" in reply
    assert ".pdf" in reply
    assert "Sign-offs: 1" in reply
    files = list((tmp_path / "exports").iterdir())
    assert any(path.suffix == ".md" for path in files)
    assert any(path.suffix == ".pdf" for path in files)
    markdown = next(path for path in files if path.suffix == ".md").read_text(encoding="utf-8")
    assert "Sagar-4" in markdown
    assert "reef.jpg" in markdown
