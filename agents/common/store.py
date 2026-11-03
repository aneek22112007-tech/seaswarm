"""Read and write operation state.

When PERSISTENCE=off, reads pretend the database and prior events are empty.
Sector inserts still happen, so a second plan duplicates rows instead of updating them.
Approval and event writes are skipped, so a sign-off has nowhere to land.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.common.models import Approval, Boat, Event, Operation, Position, Sector, utcnow
from agents.common.settings import get_settings


def persistence_enabled() -> bool:
    return get_settings().persistence_enabled


def ensure_boat(session: Session, record: dict) -> Boat | None:
    if not persistence_enabled():
        return None
    existing = session.get(Boat, record["id"])
    if existing:
        return existing
    boat = Boat(
        id=record["id"],
        name=record["name"],
        owner=record["owner"],
        licence_no=record["licence_no"],
        district=record["district"],
        home_port=record["home_port"],
        crew_json=json.dumps(record.get("crew") or []),
        gear=record.get("gear") or "",
    )
    session.add(boat)
    session.flush()
    return boat


def latest_position(session: Session, boat_id: str) -> Position | None:
    if not persistence_enabled():
        return None
    return session.scalars(
        select(Position)
        .where(Position.boat_id == boat_id)
        .order_by(Position.reported_at.desc(), Position.id.desc())
    ).first()


def find_open_operation(session: Session, boat_id: str) -> Operation | None:
    if not persistence_enabled():
        return None
    return session.scalars(
        select(Operation)
        .where(Operation.boat_id == boat_id, Operation.status.in_(("open", "searching")))
        .order_by(Operation.id.desc())
    ).first()


def create_operation(
    session: Session,
    *,
    boat_id: str,
    opened_by: str,
    status: str = "searching",
    opened_at: datetime | None = None,
) -> Operation | None:
    if not persistence_enabled():
        return None
    operation = Operation(
        boat_id=boat_id,
        status=status,
        opened_at=opened_at or utcnow(),
        opened_by=opened_by,
    )
    session.add(operation)
    session.flush()
    return operation


def list_sectors(session: Session, op_id: int) -> list[Sector]:
    if not persistence_enabled():
        return []
    return list(
        session.scalars(select(Sector).where(Sector.op_id == op_id).order_by(Sector.id)).all()
    )


def insert_sector(session: Session, **kwargs) -> Sector:
    sector = Sector(**kwargs)
    session.add(sector)
    session.flush()
    return sector


def list_events(session: Session, op_id: int, kind: str | None = None) -> list[Event]:
    if not persistence_enabled():
        return []
    stmt = select(Event).where(Event.op_id == op_id)
    if kind:
        stmt = stmt.where(Event.kind == kind)
    return list(session.scalars(stmt.order_by(Event.id)).all())


def record_event(
    session: Session,
    *,
    op_id: int,
    actor: str,
    actor_type: str,
    kind: str,
    body: str,
    message_id: str | None = None,
    created_at: datetime | None = None,
) -> Event | None:
    if not persistence_enabled():
        return None
    row = Event(
        op_id=op_id,
        actor=actor,
        actor_type=actor_type,
        kind=kind,
        body=body,
        message_id=message_id,
        created_at=created_at or utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def save_approval(session: Session, approval: Approval) -> Approval | None:
    if not persistence_enabled():
        return None
    session.add(approval)
    session.flush()
    return approval


def find_pending_approval(session: Session, op_id: int, action_type: str) -> Approval | None:
    if not persistence_enabled():
        return None
    return session.scalars(
        select(Approval)
        .where(
            Approval.op_id == op_id,
            Approval.action_type == action_type,
            Approval.status == "pending",
        )
        .order_by(Approval.id.desc())
    ).first()
