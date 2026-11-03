"""The action agent drafts pending work and releases it only after the right sign-off."""

from __future__ import annotations

import inspect

from fastapi.testclient import TestClient
from sqlalchemy import select

from agents.action_agent.handler import handle_event, open_case, release_signed
from agents.action_agent.main import app
from agents.common.db import init_db, session_scope
from agents.common.models import Approval
from agents.common.store import list_approvals, list_events, list_evidence
from tests.factories import add_boat, add_operation


def _db(tmp_path, monkeypatch, name: str):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / name}")
    monkeypatch.setenv("PERSISTENCE", "on")
    monkeypatch.setenv("LLM_API_KEY", "")
    return init_db()


def _mention(session):
    room_boat = add_boat(session)
    operation = add_operation(session, opened_by="ramesh")
    event = {
        "actor_type": "agent",
        "username": "options",
        "text": "Three options for Sagar-4\n@action",
        "message_id": "m-options",
    }
    return room_boat, operation, event


def test_draft_function_cannot_release_and_close_runs_after_the_gate():
    draft = inspect.getsource(open_case)
    release = inspect.getsource(release_signed)
    assert "perform_irreversible" not in draft
    assert "set_operation_status" not in draft
    assert release.index("perform_irreversible") < release.index("set_operation_status")


def test_mention_stores_two_pending_cards_and_does_not_execute(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "draft.db")
    with session_scope(engine) as session:
        _mention(session)
    reply = handle_event(
        {
            "actor_type": "agent",
            "username": "options",
            "text": "Three options for Sagar-4\n@action",
            "message_id": "m-options",
        }
    )
    assert isinstance(reply, list)
    assert reply[0].startswith("PENDING approval — escalation")
    assert "Approved — escalation" in reply[0]
    assert "INR 200000" in reply[1]
    assert "2026-02-14" in reply[1]
    assert reply[2].startswith("## Operation Sagar-4")
    assert "15:00" in reply[2]
    with session_scope(engine) as session:
        operation_id = 1
        approvals = list_approvals(session, operation_id)
        kinds = [row.kind for row in list_events(session, operation_id)]
    assert [row.action_type for row in approvals] == ["escalation", "scheme-outreach"]
    assert {row.status for row in approvals} == {"pending"}
    assert "gated_executed" not in kinds
    again = handle_event(
        {"actor_type": "agent", "username": "options", "text": "@action", "message_id": "m-2"}
    )
    assert isinstance(again, list)
    with session_scope(engine) as session:
        assert len(list_approvals(session, 1)) == 2


def test_family_rep_cannot_approve_escalation(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "deny.db")
    with session_scope(engine) as session:
        _mention(session)
    handle_event({"actor_type": "agent", "username": "options", "text": "@action"})
    reply = handle_event(
        {
            "actor_type": "human",
            "username": "sunita",
            "text": "Approved — escalation",
            "message_id": "m-sunita",
        }
    )
    assert isinstance(reply, list)
    assert reply[0] == "Only community_leader can approve escalation."
    with session_scope(engine) as session:
        approval = session.scalars(select(Approval)).first()
        kinds = [row.kind for row in list_events(session, approval.op_id)]
    assert approval.status == "pending"
    assert approval.approver is None
    assert "gated_executed" not in kinds


def test_community_leader_signoff_releases_the_escalation(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "sign.db")
    with session_scope(engine) as session:
        _mention(session)
    handle_event({"actor_type": "agent", "username": "options", "text": "@action"})
    reply = handle_event(
        {
            "actor_type": "human",
            "username": "ramesh",
            "text": "Approved — escalation",
            "message_id": "m-ramesh",
        }
    )
    assert isinstance(reply, list)
    assert "ramesh (community_leader) approved escalation." in reply[0]
    assert "Released approval:" in reply[1]
    assert "escalation" in reply[1]
    assert "- [x] Escalation signed off" in reply[-1]
    with session_scope(engine) as session:
        approval = session.scalars(
            select(Approval).where(Approval.action_type == "escalation")
        ).one()
        kinds = [row.kind for row in list_events(session, approval.op_id)]
    assert approval.status == "approved"
    assert approval.approver == "ramesh"
    assert approval.approver_role == "community_leader"
    assert approval.message_id == "m-ramesh"
    assert approval.decided_at is not None
    assert "gated_executed" in kinds


def test_scheme_outreach_can_be_signed_by_the_family_rep(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "scheme.db")
    with session_scope(engine) as session:
        _mention(session)
    handle_event({"actor_type": "agent", "username": "options", "text": "@action"})
    reply = handle_event(
        {
            "actor_type": "human",
            "username": "sunita",
            "text": "Approved — scheme-outreach",
            "message_id": "m-scheme",
        }
    )
    assert isinstance(reply, list)
    assert "sunita (family_rep) approved scheme-outreach." in reply[0]
    assert "Released" in reply[1]
    with session_scope(engine) as session:
        approval = session.scalars(
            select(Approval).where(Approval.action_type == "scheme-outreach")
        ).one()
    assert approval.status == "approved"
    assert approval.approver == "sunita"


def test_close_stays_pending_until_the_leader_signs(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "close.db")
    with session_scope(engine) as session:
        _boat, operation = _mention(session)[:2]
        operation_id = operation.id
    pending = handle_event(
        {"actor_type": "human", "username": "sunita", "text": "please close the search"}
    )
    assert isinstance(pending, list)
    assert "PENDING approval — close-operation" in pending[0]
    denied = handle_event(
        {
            "actor_type": "human",
            "username": "sunita",
            "text": "Approved — close-operation",
            "message_id": "m-no",
        }
    )
    assert denied[0] == "Only community_leader can approve close-operation."
    with session_scope(engine) as session:
        from agents.common.models import Operation

        assert session.get(Operation, operation_id).status == "open"
    signed = handle_event(
        {
            "actor_type": "human",
            "username": "ramesh",
            "text": "Approved — close-operation",
            "message_id": "m-yes",
        }
    )
    assert "Released" in signed[1]
    assert "Status: closed" in signed[-1]
    with session_scope(engine) as session:
        from agents.common.models import Operation

        assert session.get(Operation, operation_id).status == "closed"
        kinds = [row.kind for row in list_events(session, operation_id)]
    assert "operation_closed" in kinds
    assert "gated_executed" in kinds


def test_evidence_is_recorded_and_a_bad_fix_is_refused(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "evidence.db")
    with session_scope(engine) as session:
        _mention(session)
    bad = handle_event({"actor_type": "human", "username": "ramesh", "text": "gps: 120, 10"})
    assert "17.8136, 73.0394" in bad
    photo = handle_event(
        {
            "actor_type": "human",
            "username": "sunita",
            "text": "photo: https://example.test/reef.jpg",
            "message_id": "m-photo",
        }
    )
    assert photo[0] == "Recorded photo from sunita: https://example.test/reef.jpg"
    assert "photo 1" in photo[1]
    gps = handle_event(
        {"actor_type": "human", "username": "ramesh", "text": "gps: 17.8136, 73.0394"}
    )
    assert gps[0].startswith("Recorded gps from ramesh")
    with session_scope(engine) as session:
        rows = list_evidence(session, 1)
    assert [row.kind for row in rows] == ["photo", "gps"]


def test_own_posts_and_persistence_off_do_not_draft(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch, "quiet.db")
    with session_scope(init_db()) as session:
        _mention(session)
    assert (
        handle_event(
            {
                "actor_type": "agent",
                "username": "action",
                "text": "Approved — escalation",
            }
        )
        is None
    )
    monkeypatch.setenv("PERSISTENCE", "off")
    reply = handle_event({"actor_type": "agent", "username": "options", "text": "@action"})
    assert reply == "No open search is stored. Ask context for a situation report first."


def test_action_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["agent"] == "action"
