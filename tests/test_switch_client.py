"""The agent-side Switch client and the SSE payload parser."""

from __future__ import annotations

from types import SimpleNamespace

import httpx

from agents.common.switch_client import SwitchClient, events_from_sse


def test_post_sends_the_agent_name_and_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["token"] = request.headers["x-switch-token"]
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"message_id": "m-1"})

    client = SwitchClient(
        base_url="http://switch.test",
        token="test-token",
        room_id="sar-harnai",
        agent="echo",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    posted = client.post("echo: hello", pin=True)
    assert posted["message_id"] == "m-1"
    assert seen["path"] == "/v1/rooms/sar-harnai/messages"
    assert seen["token"] == "test-token"
    assert '"agent":"echo"' in seen["body"] or '"agent": "echo"' in seen["body"]


def test_history_returns_the_room_log():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"text": "overdue", "username": "ramesh"}])

    client = SwitchClient(
        base_url="http://switch.test",
        token="test-token",
        room_id="sar-harnai",
        agent="context",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert client.history()[0]["username"] == "ramesh"


def test_events_from_sse_skips_comments_and_parses_json():
    messages = [
        SimpleNamespace(data=""),
        SimpleNamespace(data=": ping"),
        SimpleNamespace(data='{"username": "ramesh", "text": "echo ping"}'),
    ]
    events = list(events_from_sse(messages))
    assert events == [{"username": "ramesh", "text": "echo ping"}]
