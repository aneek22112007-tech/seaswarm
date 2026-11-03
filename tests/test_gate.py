"""Nothing irreversible runs without an approved row, and the wrong role cannot sign."""

from __future__ import annotations

import inspect

from agents.common import gate
from agents.common.gate import (
    GateError,
    decide,
    denial_message,
    execute_gated,
    parse_decision,
    perform_irreversible,
    request_approval,
)
from agents.common.store import find_pending_approval, list_events
from tests.factories import add_boat, add_operation


def _pending(session):
    add_boat(session)
    operation = add_operation(session)
    approval = request_approval(
        session,
        op_id=operation.id,
        action_type="escalation",
        payload={"to": "Coast Guard / marine police, Harnai"},
        requested_by_agent="action",
    )
    session.commit()
    return operation, approval


def test_phrase_parser_requires_the_em_dash():
    assert parse_decision("Approved — escalation") == ("escalation", True)
    assert parse_decision("Rejected — escalation") == ("escalation", False)
    assert parse_decision("approved - escalation") is None
    assert parse_decision("looks good") is None


def test_request_does_not_execute(session):
    _operation, approval = _pending(session)
    assert approval.status == "pending"
    assert "execute_gated" not in inspect.getsource(gate.request_approval)
    refused = pytest_raises_gate(session, approval.id)
    assert "approved row" in str(refused)
    kinds = [row.kind for row in list_events(session, approval.op_id)]
    assert "gated_executed" not in kinds
    assert "approval_requested" in kinds


def pytest_raises_gate(session, approval_id):
    try:
        perform_irreversible(session, approval_id)
    except GateError as exc:
        assert "approved row" in str(exc)
        return exc
    raise AssertionError("perform_irreversible released a pending action")


def test_family_rep_cannot_approve_escalation(session):
    operation, approval = _pending(session)
    decision = decide(
        session,
        op_id=operation.id,
        action_type="escalation",
        username="sunita",
        message_id="m-sunita",
        approved=True,
    )
    session.commit()
    assert decision.ok is False
    assert decision.reply == "Only community_leader can approve escalation."
    assert denial_message("escalation") == decision.reply
    stored = find_pending_approval(session, operation.id, "escalation")
    assert stored is not None
    assert stored.status == "pending"
    assert stored.approver is None
    assert approval.id == stored.id


def test_community_leader_signoff_is_stored(session):
    operation, approval = _pending(session)
    decision = decide(
        session,
        op_id=operation.id,
        action_type="escalation",
        username="ramesh",
        message_id="m-ramesh",
        approved=True,
    )
    session.commit()
    assert decision.ok is True
    assert approval.status == "approved"
    assert approval.approver == "ramesh"
    assert approval.approver_role == "community_leader"
    assert approval.message_id == "m-ramesh"
    assert approval.decided_at is not None
    released = perform_irreversible(session, approval.id)
    session.commit()
    assert "approval:" in released
    kinds = [row.kind for row in list_events(session, operation.id)]
    assert "gated_executed" in kinds


def test_rejected_and_missing_rows_cannot_execute(session):
    operation, approval = _pending(session)
    decide(
        session,
        op_id=operation.id,
        action_type="escalation",
        username="ramesh",
        message_id="m-no",
        approved=False,
    )
    session.commit()
    try:
        execute_gated(session, approval.id)
        raise AssertionError("rejected approval was executed")
    except GateError:
        pass
    try:
        execute_gated(session, 999999)
        raise AssertionError("missing approval was executed")
    except GateError:
        pass


def test_persistence_off_loses_the_signoff(session, monkeypatch):
    operation, _approval = _pending(session)
    monkeypatch.setenv("PERSISTENCE", "off")
    decision = decide(
        session,
        op_id=operation.id,
        action_type="escalation",
        username="ramesh",
        message_id="m-lost",
        approved=True,
    )
    assert decision.ok is False
    assert "not applied" in decision.reply
