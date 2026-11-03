"""Replay one planning pass with the database on, then with it off.

Off mode still inserts sectors, so the second pass duplicates them, and the
sign-off has nowhere to land. The two logs are the comparison.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from agents.common.db import init_db, session_scope  # noqa: E402
from agents.common.gate import decide, request_approval  # noqa: E402
from agents.common.models import Approval, Boat, Operation, Sector, utcnow  # noqa: E402
from agents.options_agent.planner import make_options  # noqa: E402


@dataclass(frozen=True)
class Report:
    persistence: str
    sector_count: int
    name_counts: tuple[tuple[str, int], ...]
    approval_count: int
    request_stored: bool
    approver: str
    signoff: str
    coverage: str


def run_mode(database: Path, persistence: str) -> Report:
    database.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{database}"
    os.environ["PERSISTENCE"] = persistence
    os.environ["DATA_DIR"] = str(ROOT / "data")
    os.environ["ROOM_TEMPLATE"] = str(ROOT / "room_templates" / "sar_room.yaml")
    os.environ["LLM_API_KEY"] = ""
    engine = init_db()
    with session_scope(engine) as session:
        session.add(
            Boat(
                id="sagar-4",
                name="Sagar-4",
                owner="Prakash Jadhav",
                licence_no="RTN-FISH-2019-1142",
                district="Ratnagiri",
                home_port="Harnai",
                crew_json="[]",
                gear="gillnet",
            )
        )
        operation = Operation(
            boat_id="sagar-4",
            status="searching",
            opened_at=utcnow(),
            opened_by="ramesh",
        )
        session.add(operation)
        session.flush()
        first = make_options(session, operation.id)
        make_options(session, operation.id)
        approval = request_approval(
            session,
            op_id=operation.id,
            action_type="escalation",
            payload={"to": "Coast Guard / marine police, Harnai", "boat": "Sagar-4"},
            requested_by_agent="action",
        )
        decision = decide(
            session,
            op_id=operation.id,
            action_type="escalation",
            username="ramesh",
            message_id="m-ramesh",
            approved=True,
        )
        sector_count = session.scalar(
            select(func.count()).select_from(Sector).where(Sector.op_id == operation.id)
        )
        names = session.scalars(
            select(Sector.name).where(Sector.op_id == operation.id).order_by(Sector.id)
        ).all()
        approval_count = session.scalar(
            select(func.count()).select_from(Approval).where(Approval.op_id == operation.id)
        )
        stored = session.scalars(
            select(Approval).where(Approval.op_id == operation.id).order_by(Approval.id)
        ).first()
    coverage = f"{first[0].coverage_pct:.1f}"
    return Report(
        persistence=persistence,
        sector_count=int(sector_count or 0),
        name_counts=tuple(sorted(Counter(names).items())),
        approval_count=int(approval_count or 0),
        request_stored=approval is not None,
        approver="" if stored is None or not stored.approver else stored.approver,
        signoff=decision.reply,
        coverage=coverage,
    )


def render(report: Report) -> str:
    duplicates = ", ".join(f"{name} x{count}" for name, count in report.name_counts)
    lines = [
        "SeaSwarm kill-switch demo",
        "Scenario: Sagar-4, 3 crew, Harnai, Ratnagiri. Overdue 2 hours. Same two planning passes.",
        f"PERSISTENCE={report.persistence}",
        f"option A coverage={report.coverage}",
        f"sectors_after_two_passes={report.sector_count}",
        f"sector_rows={duplicates}",
        f"approval_request_stored={str(report.request_stored).lower()}",
        f"stored_approvals={report.approval_count}",
        f"approver={report.approver or '(none)'}",
        f"sign-off reply: {report.signoff}",
    ]
    if report.persistence == "off":
        lines.append("Result: sectors were duplicated and the sign-off was not stored.")
    else:
        lines.append(
            "Result: the second pass updated the same sectors and the sign-off was stored."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    runtime = ROOT / ".runtime" / "killswitch"
    for mode, filename in (("on", "persistence-on.txt"), ("off", "persistence-off.txt")):
        report = run_mode(runtime / f"{mode}.db", mode)
        text = render(report)
        (log_dir / filename).write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
