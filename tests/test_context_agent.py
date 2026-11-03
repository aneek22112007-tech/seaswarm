"""Context turns an overdue report into a drift summary and tags @options."""

from __future__ import annotations

from agents.common.db import init_db, session_scope
from agents.common.llm import phrase
from agents.common.store import record_event
from agents.context_agent.handler import build_reply, handle_event
from agents.context_agent.parse import (
    boat_from_text,
    is_trigger,
    parse_daylight_hours,
    parse_overdue_hours,
)
from agents.context_agent.summary import render_summary
from core.load import load_json
from tests.factories import add_boat, add_operation

REPORT = (
    "Sagar-4 is overdue by 2 hours and not back. Missing near the reef. "
    "4 hours of daylight left."
)


def test_parsers_read_the_demo_sentence():
    assert is_trigger(REPORT)
    assert parse_overdue_hours(REPORT) == 2.0
    assert parse_daylight_hours(REPORT) == 4.0
    assert not is_trigger("the kettle is on")
    catalog = load_json("boats.json")["boats"]
    assert boat_from_text("seen Chandra-2 and Sagar-4", catalog)["name"] == "Chandra-2"


def test_summary_keeps_the_computed_radius():
    text = render_summary(
        {
            "boat_name": "Sagar-4",
            "crew_names": ["Prakash Jadhav"],
            "crew_count": 3,
            "owner": "Prakash Jadhav",
            "licence_no": "RTN-FISH-2019-1142",
            "overdue_hours": 2,
            "opened_by": "ramesh",
            "heading_deg": 250,
            "lat": 17.8136,
            "lon": 73.0394,
            "source": "radio",
            "center_lat": 17.8,
            "center_lon": 73.02,
            "bearing_deg": 200,
            "distance_km": 3.4,
            "radius_km": 0.95,
            "spread_deg": 24,
            "daylight_hours": 4,
            "wind_speed_kn": 14,
            "wind_from_deg": 270,
            "sea_state": 4,
            "wave_height_m": 1.4,
            "tide_state": "ebb",
            "current_speed_kn": 0.6,
            "current_to_deg": 200,
        }
    )
    assert "radius 0.95 km" in text
    assert text.endswith("@options")


def test_llm_fallback_when_a_figure_is_dropped():
    def complete(**_kwargs):
        return "They are somewhere else, about 999 km away."

    assert (
        phrase(
            agent="context",
            facts={"radius_km": 0.95},
            fallback="radius 0.95\n@options",
            required=["0.95", "@options"],
            complete=complete,
        )
        == "radius 0.95\n@options"
    )


def test_llm_keeps_wording_that_preserves_figures():
    def complete(**_kwargs):
        return "Sagar-4 radius 0.95, daylight 4.0\n@options"

    text = phrase(
        agent="context",
        facts={},
        fallback="fallback",
        required=["0.95", "@options"],
        complete=complete,
    )
    assert text.startswith("Sagar-4")


def _report_event(text: str = REPORT) -> dict:
    return {
        "actor_type": "human",
        "username": "ramesh",
        "text": text,
        "message_id": "m1",
    }


def test_overdue_report_posts_a_cone(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'context.db'}")
    monkeypatch.setenv("PERSISTENCE", "on")
    reply = handle_event(_report_event())
    assert reply is not None
    assert reply.startswith("Sagar-4")
    assert "Drift cone:" in reply
    assert "radius 0.95 km" in reply
    assert "Daylight left: 4.0 h" in reply
    assert reply.endswith("@options")
    assert handle_event({"actor_type": "agent", "text": REPORT}) is None


def test_room_history_can_name_the_boat(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'history.db'}")
    monkeypatch.setenv("PERSISTENCE", "on")
    engine = init_db()
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session)
        record_event(
            session,
            op_id=operation.id,
            actor="ramesh",
            actor_type="human",
            kind="report",
            body="Sagar-4 left the reef",
        )
    reply = handle_event(_report_event("they are overdue and not back"))
    assert reply is not None
    assert reply.startswith("Sagar-4")


def test_persistence_off_ignores_room_history(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'off.db'}")
    monkeypatch.setenv("PERSISTENCE", "off")
    engine = init_db()
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session)
        record_event(
            session,
            op_id=operation.id,
            actor="ramesh",
            actor_type="human",
            kind="report",
            body="Sagar-4 left the reef",
        )
    reply = handle_event(_report_event("they are overdue and not back"))
    assert "could not find the boat" in reply


def test_build_reply_uses_the_open_operation(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'open.db'}")
    monkeypatch.setenv("PERSISTENCE", "on")
    engine = init_db()
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session, opened_by="ramesh")
        reply = build_reply(session, _report_event())
        assert operation.id is not None
    assert "opened by ramesh" in reply
