"""Write the audit trail for every stored operation to Markdown and PDF."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.common.audit import export_audit  # noqa: E402
from agents.common.db import init_db, session_scope  # noqa: E402
from agents.common.settings import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    directory = Path(settings.export_dir)
    engine = init_db()
    with session_scope(engine) as session:
        exported = export_audit(
            session,
            directory,
            actor="export_audit",
            actor_type="agent",
        )
    print(exported.markdown_path)
    print(exported.pdf_path)
    print(f"events={exported.event_count} signoffs={exported.signoff_count}")


if __name__ == "__main__":
    main()
