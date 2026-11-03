"""Shared FastAPI shell and the SSE dispatch loop."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agents.common.switch_client import SwitchClient, iter_events

logger = logging.getLogger(__name__)
Handler = Callable[[dict], str | list[str] | None]


def dispatch(event: dict, handler: Handler, client: SwitchClient) -> list[str]:
    """Run one event through a handler and post any replies. Own messages are ignored."""
    if event.get("username") == client.agent:
        return []
    reply = handler(event)
    texts: list[str] = []
    if isinstance(reply, str):
        texts = [reply]
    elif isinstance(reply, list):
        texts = [item for item in reply if isinstance(item, str)]
    posted = []
    for text in texts:
        if text.strip():
            client.post(text)
            posted.append(text)
    return posted


def loop(agent_name: str, handler: Handler, client: SwitchClient | None = None) -> None:
    speaker = client or SwitchClient(agent=agent_name)
    url = f"{speaker.base_url}/v1/events?room_id={speaker.room_id}&agent={agent_name}"
    while True:
        try:
            for event in iter_events(url):
                dispatch(event, handler, speaker)
        except Exception:
            logger.exception("%s event stream dropped", agent_name)
            time.sleep(2)
        if os.getenv("SEASWARM_LOOP_ONCE") == "1":
            return


def serve(agent_name: str, handler: Handler) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if os.getenv("SEASWARM_DISABLE_LOOP") != "1":
            thread = threading.Thread(
                target=loop,
                args=(agent_name, handler),
                name=f"{agent_name}-loop",
                daemon=True,
            )
            thread.start()
        yield

    app = FastAPI(title=f"SeaSwarm {agent_name}", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "agent": agent_name}

    return app
