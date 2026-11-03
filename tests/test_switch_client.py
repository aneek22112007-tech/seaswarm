"""The agent-side Switch client and the SSE payload parser."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import httpx

from agents.common.switch_client import SwitchClient, events_from_sse, iter_events


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


def test_events_from_sse_reads_sseclient_events():
    """sseclient-py 1.9 yields from events() and cannot be iterated itself."""
    from sseclient import SSEClient

    class Source:
        def __iter__(self):
            yield b': connected\n\ndata: {"text": "overdue"}\n\n'

        def close(self) -> None:
            return None

    events = list(events_from_sse(SSEClient(Source())))
    assert events == [{"text": "overdue"}]


def test_iter_events_reads_a_live_sse_response():
    body = b': connected\n\ndata: {"text": "overdue"}\n\n'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        events = list(iter_events(f"http://127.0.0.1:{port}/v1/events"))
    finally:
        server.shutdown()
        server.server_close()
    assert events == [{"text": "overdue"}]
