"""HTTP client agents use to answer in a Switch room, plus the SSE parser."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator

import httpx

from agents.common.settings import get_settings


class SwitchClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        room_id: str | None = None,
        agent: str,
        http: httpx.Client | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.switch_url).rstrip("/")
        self.token = token or settings.switch_token
        self.room_id = room_id or settings.room_id
        self.agent = agent
        self.http = http or httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"X-Switch-Token": self.token}

    def post(self, text: str, *, pin: bool = False, root_id: str | None = None) -> dict:
        response = self.http.post(
            f"{self.base_url}/v1/rooms/{self.room_id}/messages",
            json={"agent": self.agent, "text": text, "pin": pin, "root_id": root_id},
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def edit(self, message_id: str, text: str) -> dict:
        response = self.http.put(
            f"{self.base_url}/v1/rooms/{self.room_id}/messages/{message_id}",
            json={"agent": self.agent, "text": text},
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def post_human(self, username: str, text: str) -> dict:
        response = self.http.post(
            f"{self.base_url}/v1/rooms/{self.room_id}/human",
            json={"username": username, "text": text},
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def subscribers(self) -> list[str]:
        response = self.http.get(f"{self.base_url}/v1/rooms/{self.room_id}/subscribers")
        response.raise_for_status()
        return list(response.json().get("agents") or [])

    def history(self) -> list[dict]:
        response = self.http.get(f"{self.base_url}/v1/rooms/{self.room_id}/history")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self.http.close()


def events_from_sse(messages: Iterable) -> Iterator[dict]:
    """Yield JSON events from SSE message objects. Blank comments are ignored."""
    for message in messages:
        data = getattr(message, "data", "") or ""
        if not data or data.startswith(":"):
            continue
        yield json.loads(data)


def iter_events(url: str) -> Iterator[dict]:
    """Block on a Switch SSE stream. sseclient uses requests; posts use httpx."""
    from sseclient import SSEClient

    yield from events_from_sse(SSEClient(url))
