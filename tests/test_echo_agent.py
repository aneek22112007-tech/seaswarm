"""Echo replies once, and the runner posts that reply."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agents.common.runner import dispatch
from agents.echo_agent.handler import handle_event
from agents.echo_agent.main import app


class _Recorder:
    agent = "echo"

    def __init__(self) -> None:
        self.posts: list[str] = []

    def post(self, text: str, **_kwargs) -> dict:
        self.posts.append(text)
        return {"message_id": "local"}


def test_echo_repeats_a_marked_human_line():
    reply = handle_event({"actor_type": "human", "username": "ramesh", "text": "echo Sagar-4"})
    assert reply == "echo: Sagar-4"


def test_echo_ignores_ordinary_traffic_and_agents():
    assert handle_event({"actor_type": "human", "text": "Sagar-4 is overdue"}) is None
    assert handle_event({"actor_type": "agent", "text": "echo hello"}) is None


def test_dispatch_posts_the_echo_and_skips_its_own_message():
    recorder = _Recorder()
    posted = dispatch(
        {"username": "ramesh", "actor_type": "human", "text": "echo tide"},
        handle_event,
        recorder,  # type: ignore[arg-type]
    )
    assert posted == ["echo: tide"]
    assert recorder.posts == ["echo: tide"]
    again = dispatch(
        {"username": "echo", "actor_type": "agent", "text": "echo: tide"},
        handle_event,
        recorder,  # type: ignore[arg-type]
    )
    assert again == []


def test_echo_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["agent"] == "echo"
