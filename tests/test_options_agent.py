"""Three options, re-plans, and a spoken refusal when two boats share a sector."""

from __future__ import annotations

from sqlalchemy import select

from agents.common.db import init_db, session_scope
from agents.common.models import Sector
from agents.options_agent.commands import Command, parse_command
from agents.options_agent.handler import build_reply, handle_event
from agents.options_agent.planner import make_options
from tests.factories import add_boat, add_operation


def _db(tmp_path, monkeypatch, name: str):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / name}")
    monkeypatch.setenv("PERSISTENCE", "on")
    return init_db()


def test_commands_from_the_room():
    assert parse_command("Sector-2 clear", "human").sector == "Sector-2"
    assert parse_command("Sector 1 clear", "human").sector == "Sector-1"
    reassign = parse_command("reassign Meerabai to Sector-1", "human")
    assert reassign.boat == "Meerabai"
    assert reassign.sector == "Sector-1"
    assert parse_command("reject option B", "human").option_id == "B"
    assert parse_command("summary @options", "agent").kind == "plan"
    assert parse_command("hello", "human") is None


def test_plan_message_has_three_options(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "plan.db")
    with session_scope(engine) as session:
        add_boat(session)
        add_operation(session)
        reply = build_reply(session, Command("plan"))
    assert "Option A" in reply
    assert "Option B" in reply
    assert "Option C" in reply
    assert reply.endswith("@action")
    assert "INR" in reply


def test_second_plan_does_not_duplicate_sectors(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "once.db")
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session)
        make_options(session, operation.id)
        make_options(session, operation.id)
        op_id = operation.id
    with session_scope(engine) as session:
        rows = session.scalars(select(Sector).where(Sector.op_id == op_id)).all()
    assert len(rows) == 3


def test_persistence_off_duplicates_sectors(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'dup.db'}")
    monkeypatch.setenv("PERSISTENCE", "off")
    engine = init_db()
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session)
        op_id = operation.id
        make_options(session, op_id)
        make_options(session, op_id)
    with session_scope(engine) as session:
        rows = session.scalars(select(Sector).where(Sector.op_id == op_id)).all()
    assert len(rows) == 6


def test_second_boat_on_a_sector_is_rejected(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "conflict.db")
    with session_scope(engine) as session:
        add_boat(session)
        add_operation(session)
        build_reply(session, Command("reassign", sector="Sector-1", boat="Meerabai"))
        reply = build_reply(session, Command("reassign", sector="Sector-1", boat="Chandra-2"))
    assert reply.startswith("Conflict: Sector-1 is already assigned to Meerabai.")
    assert "Chandra-2" in reply


def test_reject_option_b_revises_the_plan(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "reject.db")
    with session_scope(engine) as session:
        add_boat(session)
        add_operation(session)
        reply = build_reply(session, Command("reject", option_id="B"))
    assert "revised:" in reply
    assert "Option A" in reply and "Option C" in reply


def test_clearing_every_sector_does_not_close_the_search(tmp_path, monkeypatch):
    engine = _db(tmp_path, monkeypatch, "clear.db")
    with session_scope(engine) as session:
        add_boat(session)
        add_operation(session)
        build_reply(session, Command("clear", sector="Sector-1"))
        build_reply(session, Command("clear", sector="Sector-2"))
        reply = build_reply(session, Command("clear", sector="Sector-3"))
    assert "All sectors are clear" in reply
    assert "community_leader" in reply


def test_handler_ignores_its_own_posts():
    assert handle_event({"username": "options", "actor_type": "agent", "text": "@options"}) is None
