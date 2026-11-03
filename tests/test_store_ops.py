"""Approvals and evidence can be listed, and they disappear when persistence is off."""

from __future__ import annotations

from agents.common.store import (
    add_evidence,
    list_approvals,
    list_evidence,
    set_operation_status,
)
from tests.factories import add_boat, add_operation


def test_evidence_round_trip(session):
    add_boat(session)
    operation = add_operation(session)
    stored = add_evidence(
        session,
        op_id=operation.id,
        kind="gps",
        uri="17.8136,73.0394",
        submitted_by="ramesh",
    )
    session.commit()
    assert stored is not None
    rows = list_evidence(session, operation.id)
    assert rows[0].kind == "gps"
    assert rows[0].uri == "17.8136,73.0394"
    assert rows[0].submitted_by == "ramesh"


def test_operation_status_can_be_updated(session):
    add_boat(session)
    operation = add_operation(session)
    updated = set_operation_status(session, operation.id, "searching")
    assert updated is not None
    assert updated.status == "searching"


def test_persistence_off_hides_evidence_and_approvals(session, monkeypatch):
    add_boat(session)
    operation = add_operation(session)
    add_evidence(
        session,
        op_id=operation.id,
        kind="note",
        uri="saw a float",
        submitted_by="sunita",
    )
    session.commit()
    monkeypatch.setenv("PERSISTENCE", "off")
    assert list_evidence(session, operation.id) == []
    assert list_approvals(session, operation.id) == []
    assert (
        add_evidence(
            session,
            op_id=operation.id,
            kind="note",
            uri="later",
            submitted_by="sunita",
        )
        is None
    )
    assert set_operation_status(session, operation.id, "closed") is None
