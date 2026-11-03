"""Build a timestamped audit of who did what. Reads the database directly."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.common.models import Approval, Boat, Event, Evidence, Operation, Sector
from agents.common.store import record_event


@dataclass(frozen=True)
class AuditExport:
    markdown_path: Path
    pdf_path: Path
    event_count: int
    signoff_count: int


def render_audit(session: Session, *, generated_at: datetime) -> str:
    operations = list(session.scalars(select(Operation).order_by(Operation.id)).all())
    lines = [
        "# SeaSwarm audit",
        "",
        f"Generated: {generated_at.isoformat()}",
        "",
        "Agents propose. Humans sign. This file is the record of who did each step.",
        "",
    ]
    if not operations:
        lines.append("No operations are stored.")
        lines.append("")
        return "\n".join(lines)
    for operation in operations:
        lines.extend(_operation_section(session, operation))
    return "\n".join(lines)


def export_audit(
    session: Session,
    directory: Path,
    *,
    actor: str,
    actor_type: str,
    now: datetime | None = None,
) -> AuditExport:
    """Write Markdown and PDF. The export itself is appended before the files are rendered."""
    generated_at = now or datetime.now(timezone.utc)
    stamp = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=True)
    operations = list(session.scalars(select(Operation).order_by(Operation.id)).all())
    if operations:
        record_event(
            session,
            op_id=operations[-1].id,
            actor=actor,
            actor_type=actor_type,
            kind="audit_exported",
            body=stamp,
            created_at=generated_at,
        )
    text = render_audit(session, generated_at=generated_at)
    markdown_path = directory / f"audit-{stamp}.md"
    pdf_path = directory / f"audit-{stamp}.pdf"
    markdown_path.write_text(text, encoding="utf-8")
    _write_pdf(pdf_path, text)
    signoffs = list(session.scalars(select(Approval).where(Approval.status == "approved")).all())
    event_count = len(list(session.scalars(select(Event)).all()))
    return AuditExport(markdown_path, pdf_path, event_count, len(signoffs))


def _operation_section(session: Session, operation: Operation) -> list[str]:
    boat = session.get(Boat, operation.boat_id)
    boat_name = boat.name if boat is not None else operation.boat_id
    lines = [
        f"## Operation {operation.id} - {boat_name}",
        "",
        f"- Status: {operation.status}",
        f"- Boat id: {operation.boat_id}",
        f"- Opened by: {operation.opened_by}",
        f"- Opened at: {operation.opened_at.isoformat()}",
        "",
        "### Assignments",
        "",
        "| Sector | Status | Assigned boat | Updated |",
        "| --- | --- | --- | --- |",
    ]
    sectors = list(
        session.scalars(
            select(Sector).where(Sector.op_id == operation.id).order_by(Sector.id)
        ).all()
    )
    if not sectors:
        lines.append("| (none) | | | |")
    for sector in sectors:
        lines.append(
            f"| {sector.name} | {sector.status} | {sector.assigned_boat or ''} | "
            f"{sector.updated_at.isoformat()} |"
        )
    lines.extend(["", "### Sign-offs", "", _approval_table(session, operation.id)])
    lines.extend(["", "### Evidence", "", _evidence_table(session, operation.id)])
    lines.extend(["", "### Events", "", _event_table(session, operation.id), ""])
    return lines


def _approval_table(session: Session, op_id: int) -> str:
    rows = list(
        session.scalars(select(Approval).where(Approval.op_id == op_id).order_by(Approval.id)).all()
    )
    lines = [
        "| Action | Status | Requested by | Approver | Role | Message | Decided |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) | | | | | | |")
    for row in rows:
        lines.append(
            "| {action} | {status} | {requested} | {approver} | {role} | {message} | {decided} |".format(
                action=row.action_type,
                status=row.status,
                requested=row.requested_by_agent,
                approver=row.approver or "",
                role=row.approver_role or "",
                message=row.message_id or "",
                decided=row.decided_at.isoformat() if row.decided_at else "",
            )
        )
    return "\n".join(lines)


def _evidence_table(session: Session, op_id: int) -> str:
    rows = list(
        session.scalars(select(Evidence).where(Evidence.op_id == op_id).order_by(Evidence.id)).all()
    )
    lines = [
        "| Kind | URI | Submitted by | When |",
        "| --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) | | | |")
    for row in rows:
        lines.append(
            f"| {row.kind} | {row.uri} | {row.submitted_by} | {row.created_at.isoformat()} |"
        )
    return "\n".join(lines)


def _event_table(session: Session, op_id: int) -> str:
    rows = list(session.scalars(select(Event).where(Event.op_id == op_id).order_by(Event.id)).all())
    lines = [
        "| When | Actor | Type | Kind | Message | Body |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) | | | | | |")
    for row in rows:
        body = row.body.replace("\n", " ")
        lines.append(
            f"| {row.created_at.isoformat()} | {row.actor} | {row.actor_type} | {row.kind} | "
            f"{row.message_id or ''} | {body} |"
        )
    return "\n".join(lines)


def _write_pdf(path: Path, markdown: str) -> None:
    document = FPDF()
    document.compress = False
    document.set_auto_page_break(auto=True, margin=15)
    document.add_page()
    document.set_font("Helvetica", size=10)
    document.multi_cell(0, 5, _pdf_text(markdown))
    document.output(path)


def _pdf_text(markdown: str) -> str:
    cleaned = markdown.replace("\u2014", " - ").replace("\u2013", " - ")
    return cleaned.encode("latin-1", "replace").decode("latin-1")
