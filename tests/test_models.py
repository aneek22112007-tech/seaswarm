"""Persistence for boats, operations, sectors, approvals, events, and evidence."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from agents.common.models import Approval, Event, Evidence, Position, Sector, utcnow
from tests.factories import add_boat, add_operation


def test_operation_records_who_opened_the_search(session):
    add_boat(session)
    operation = add_operation(session, opened_by="ramesh")
    session.commit()
    assert operation.id is not None
    assert operation.status == "open"
    assert operation.opened_by == "ramesh"


def test_operation_rejects_an_unknown_status(session):
    add_boat(session)
    operation = add_operation(session)
    operation.status = "drifting"
    session.add(operation)
    with pytest.raises(IntegrityError):
        session.commit()


def test_position_is_stored_against_the_boat(session):
    add_boat(session)
    position = Position(
        boat_id="sagar-4",
        lat=17.8136,
        lon=73.0394,
        source="radio",
        reported_at=utcnow(),
    )
    session.add(position)
    session.commit()
    assert position.id is not None
    assert position.lat == pytest.approx(17.8136)


def test_position_requires_a_known_boat(session):
    session.add(
        Position(
            boat_id="missing",
            lat=17.0,
            lon=73.0,
            source="radio",
            reported_at=utcnow(),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_sector_starts_unassigned(session):
    add_boat(session)
    operation = add_operation(session)
    sector = Sector(
        op_id=operation.id,
        name="Sector-1",
        polygon_json="[]",
        status="unassigned",
        assigned_boat=None,
        updated_at=utcnow(),
    )
    session.add(sector)
    session.commit()
    assert sector.assigned_boat is None
    assert sector.status == "unassigned"


def test_approval_starts_pending_without_a_signoff(session):
    add_boat(session)
    operation = add_operation(session)
    approval = Approval(
        op_id=operation.id,
        action_type="escalation",
        payload_json="{}",
        requested_by_agent="action",
        status="pending",
    )
    session.add(approval)
    session.commit()
    assert approval.approver is None
    assert approval.decided_at is None
    assert approval.message_id is None


def test_events_reject_updates_and_deletes(session):
    add_boat(session)
    operation = add_operation(session)
    record = Event(
        op_id=operation.id,
        actor="context",
        actor_type="agent",
        kind="summary",
        body="original",
        message_id="m1",
        created_at=utcnow(),
    )
    session.add(record)
    session.commit()
    record.body = "tampered"
    with pytest.raises(RuntimeError, match="append-only"):
        session.commit()
    session.rollback()
    session.delete(record)
    with pytest.raises(RuntimeError, match="append-only"):
        session.commit()


def test_evidence_records_a_photo_uri(session):
    add_boat(session)
    operation = add_operation(session)
    sector = Sector(
        op_id=operation.id,
        name="Sector-2",
        polygon_json="[]",
        status="searching",
        assigned_boat="Meerabai",
        updated_at=utcnow(),
    )
    session.add(sector)
    session.flush()
    photo = Evidence(
        op_id=operation.id,
        sector_id=sector.id,
        kind="photo",
        uri="file://reef-north.jpg",
        submitted_by="sunita",
        created_at=utcnow(),
    )
    session.add(photo)
    session.commit()
    assert photo.kind == "photo"
    assert photo.uri == "file://reef-north.jpg"


def test_evidence_rejects_an_unknown_kind(session):
    add_boat(session)
    operation = add_operation(session)
    session.add(
        Evidence(
            op_id=operation.id,
            sector_id=None,
            kind="rumour",
            uri="note",
            submitted_by="sunita",
            created_at=utcnow(),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
