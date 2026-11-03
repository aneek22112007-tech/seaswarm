"""In-process pub/sub for room events."""

from __future__ import annotations

import asyncio
import threading


class Hub:
    """Fan out room events to SSE subscribers and keep a short history."""

    def __init__(self, history_limit: int = 2000) -> None:
        self._events: list[dict] = []
        self._subs: list[tuple[str, asyncio.Queue]] = []
        self._lock = threading.Lock()
        self._history_limit = history_limit

    def publish(self, event: dict) -> dict:
        with self._lock:
            self._events.append(dict(event))
            if len(self._events) > self._history_limit:
                self._events = self._events[-self._history_limit :]
            subs = list(self._subs)
        for room_id, queue in subs:
            if room_id not in (event["room_id"], "*"):
                continue
            queue.put_nowait(dict(event))
        return dict(event)

    def subscribe(self, room_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subs.append((room_id, queue))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subs = [item for item in self._subs if item[1] is not queue]

    def history(self, room_id: str) -> list[dict]:
        with self._lock:
            return [dict(event) for event in self._events if event["room_id"] == room_id]

    def update(self, room_id: str, message_id: str, text: str) -> dict | None:
        with self._lock:
            for event in self._events:
                if event["room_id"] == room_id and event["message_id"] == message_id:
                    event["text"] = text
                    event["edited"] = True
                    return dict(event)
        return None
