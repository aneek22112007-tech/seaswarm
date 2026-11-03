"""Load the boat register and Sagar-4's last known position."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.common.db import init_db, session_scope  # noqa: E402
from agents.common.models import Position  # noqa: E402
from agents.common.room import load_room  # noqa: E402
from agents.common.store import ensure_boat, latest_position  # noqa: E402
from core.load import load_json  # noqa: E402


def seed_database() -> str:
    room = load_room()
    engine = init_db()
    with session_scope(engine) as session:
        for record in load_json("boats.json")["boats"]:
            ensure_boat(session, record)
        last = room["last_known"]
        if latest_position(session, room["boat_id"]) is None:
            session.add(
                Position(
                    boat_id=room["boat_id"],
                    lat=float(last["lat"]),
                    lon=float(last["lon"]),
                    source=last["source"],
                    reported_at=datetime.fromisoformat(last["reported_at"]),
                )
            )
            session.flush()
        stored = latest_position(session, room["boat_id"])
    if stored is None:
        raise RuntimeError("Sagar-4 position was not stored")
    return f"seeded {room['boat_id']} at {stored.lat}, {stored.lon}"


def main() -> None:
    print(seed_database())


if __name__ == "__main__":
    main()
