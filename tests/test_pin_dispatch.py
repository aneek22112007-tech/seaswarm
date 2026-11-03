"""The operation log is pinned once and later updates edit that message."""

from __future__ import annotations

from agents.common.db import init_db, session_scope
from agents.common.runner import dispatch
from agents.common.store import list_events
from tests.factories import add_boat, add_operation


class _Recorder:
    agent = "action"

    def __init__(self) -> None:
        self.posts: list[tuple[str, bool]] = []
        self.edits: list[tuple[str, str]] = []

    def post(self, text: str, pin: bool = False, root_id: str | None = None) -> dict:
        self.posts.append((text, pin))
        return {"message_id": "m-pin"}

    def edit(self, message_id: str, text: str) -> dict:
        self.edits.append((message_id, text))
        return {"message_id": message_id, "text": text}


def test_operation_log_is_pinned_then_edited(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'pin.db'}")
    monkeypatch.setenv("PERSISTENCE", "on")
    engine = init_db()
    with session_scope(engine) as session:
        add_boat(session)
        add_operation(session)
    recorder = _Recorder()
    first = dispatch(
        {"username": "options", "actor_type": "agent", "text": "@action"},
        lambda _event: ["## Operation Sagar-4", "PENDING approval — escalation"],
        recorder,  # type: ignore[arg-type]
    )
    assert first[0].startswith("## Operation")
    assert recorder.posts == [
        ("## Operation Sagar-4", True),
        ("PENDING approval — escalation", False),
    ]
    dispatch(
        {"username": "options", "actor_type": "agent", "text": "@action"},
        lambda _event: ["## Operation Sagar-4\nStatus: searching"],
        recorder,  # type: ignore[arg-type]
    )
    assert recorder.edits == [("m-pin", "## Operation Sagar-4\nStatus: searching")]
    with session_scope(engine) as session:
        pins = list_events(session, 1, kind="ops_pin")
    assert pins[0].body == "m-pin"
