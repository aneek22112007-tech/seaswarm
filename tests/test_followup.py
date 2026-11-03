"""Follow-up time is a pure function. The loop waits before it posts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agents.action_agent.followup import followup_due, followup_loop, next_followup, post_if_due
from agents.common.db import init_db, session_scope
from tests.factories import add_boat, add_operation


def test_next_prompt_is_one_interval_later():
    start = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    assert next_followup(start, 1800) == datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc)


def test_followup_is_due_only_after_the_interval():
    start = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    assert followup_due(datetime(2026, 1, 15, 14, 59, tzinfo=timezone.utc), start, 1800) is False
    assert followup_due(datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc), start, 1800) is True
    assert followup_due(start, None, 1800) is False


def test_negative_interval_is_rejected():
    with pytest.raises(ValueError):
        next_followup(datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc), 0)


def test_post_if_due_waits_then_posts_once(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'follow.db'}")
    monkeypatch.setenv("PERSISTENCE", "on")
    engine = init_db()
    opened = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)

    class _Client:
        def __init__(self) -> None:
            self.texts: list[str] = []

        def post(self, text: str, **_kwargs) -> dict:
            self.texts.append(text)
            return {"message_id": "f-1"}

    client = _Client()
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session)
        operation.opened_at = opened
        assert (
            post_if_due(session, client, datetime(2026, 1, 15, 9, 20, tzinfo=timezone.utc)) is None
        )
        posted = post_if_due(session, client, datetime(2026, 1, 15, 9, 40, tzinfo=timezone.utc))
        assert posted is not None
        assert "Sagar-4" in posted
        assert "Nothing is sent outside this room." in posted
        again = post_if_due(session, client, datetime(2026, 1, 15, 9, 40, tzinfo=timezone.utc))
        assert again is None
    assert len(client.texts) == 1


def test_persistence_off_skips_the_followup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'follow-off.db'}")
    engine = init_db()
    with session_scope(engine) as session:
        add_boat(session)
        operation = add_operation(session)
        operation.opened_at = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
    monkeypatch.setenv("PERSISTENCE", "off")
    with session_scope(engine) as session:
        assert post_if_due(session, None, datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)) is None


def test_followup_loop_sleeps_before_posting():
    seen: list[int] = []

    def _sleep(seconds: int) -> None:
        seen.append(seconds)
        raise SystemExit

    with pytest.raises(SystemExit):
        followup_loop(sleep=_sleep)
    assert seen == [1800]
