"""The demo register contains Sagar-4 and the reef position."""

from __future__ import annotations

from agents.common.db import init_db, session_scope
from agents.common.models import Boat
from agents.common.store import latest_position
from scripts.seed_demo import seed_database


def test_seed_stores_the_harnai_boat_and_the_reef_fix(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'seed.db'}")
    monkeypatch.setenv("PERSISTENCE", "on")
    message = seed_database()
    assert "sagar-4" in message
    assert "17.8136" in message
    engine = init_db()
    with session_scope(engine) as session:
        assert session.get(Boat, "meerabai") is not None
        position = latest_position(session, "sagar-4")
    assert position is not None
    assert round(position.lon, 4) == 73.0394
    again = seed_database()
    assert "17.8136" in again
