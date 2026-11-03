"""SQLite tables for one search.

`events` is append-only. Updates and deletes are rejected in the session
so the audit trail cannot be rewritten in place.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint(
            "status in ('open', 'searching', 'found', 'closed')",
            name="ck_operations_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    boat_id: Mapped[str] = mapped_column(ForeignKey("boats.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_by: Mapped[str] = mapped_column(String(64), nullable=False)


class Boat(Base):
    __tablename__ = "boats"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    licence_no: Mapped[str] = mapped_column(String(64), nullable=False)
    district: Mapped[str] = mapped_column(String(64), nullable=False)
    home_port: Mapped[str] = mapped_column(String(64), nullable=False)
    crew_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    gear: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    boat_id: Mapped[str] = mapped_column(ForeignKey("boats.id"), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Sector(Base):
    __tablename__ = "sectors"
    __table_args__ = (
        CheckConstraint(
            "status in ('unassigned', 'assigned', 'searching', 'clear', 'found')",
            name="ck_sectors_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    op_id: Mapped[int] = mapped_column(ForeignKey("operations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    polygon_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unassigned")
    assigned_boat: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'approved', 'rejected')",
            name="ck_approvals_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    op_id: Mapped[int] = mapped_column(ForeignKey("operations.id"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approver: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approver_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    op_id: Mapped[int] = mapped_column(ForeignKey("operations.id"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (CheckConstraint("kind in ('photo', 'gps', 'note')", name="ck_evidence_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    op_id: Mapped[int] = mapped_column(ForeignKey("operations.id"), nullable=False, index=True)
    sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectors.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


@event.listens_for(Event, "before_update")
def _reject_event_update(_mapper, _connection, _target) -> None:
    raise RuntimeError("events are append-only")


@event.listens_for(Event, "before_delete")
def _reject_event_delete(_mapper, _connection, _target) -> None:
    raise RuntimeError("events are append-only")
