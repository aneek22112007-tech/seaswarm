"""SQLite pragmas for the shared operation database."""

from __future__ import annotations

from agents.common.db import init_db, journal_mode, make_engine, session_scope
from agents.common.models import Boat


def test_file_database_uses_wal(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'seaswarm.db'}")
    assert journal_mode(engine) == "wal"
    engine.dispose()


def test_init_db_creates_boats(tmp_path):
    engine = init_db(make_engine(f"sqlite:///{tmp_path / 'seaswarm.db'}"))
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
    with session_scope(engine) as session:
        stored = session.get(Boat, "sagar-4")
        assert stored is not None
        assert stored.home_port == "Harnai"
    engine.dispose()
