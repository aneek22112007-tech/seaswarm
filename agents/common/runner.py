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
            if text.startswith("## Operation"):
                deliver_pinned(client, text)
            else:
                client.post(text)
            posted.append(text)
    return posted


def deliver_pinned(client: SwitchClient, text: str) -> None:
    """Pin the operation log once, then edit that same message on later updates."""
    from agents.common.db import init_db, session_scope
    from agents.common.room import load_room
    from agents.common.store import find_open_operation, list_events, record_event

    engine = init_db()
    with session_scope(engine) as session:
        operation = find_open_operation(session, load_room()["boat_id"])
        pins = list_events(session, operation.id, kind="ops_pin") if operation is not None else []
        if pins:
            client.edit(pins[-1].body, text)
            return
        posted = client.post(text, pin=True)
        message_id = str(posted.get("message_id") or "")
        if operation is not None and message_id:
            record_event(
                session,
                op_id=operation.id,
                actor=client.agent,
                actor_type="agent",
                kind="ops_pin",
                body=message_id,
            )


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


def serve(
    agent_name: str,
    handler: Handler,
    extras: list[Callable[[], None]] | None = None,
) -> FastAPI:
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
            for extra in extras or []:
                threading.Thread(
                    target=extra,
                    name=f"{agent_name}-extra",
                    daemon=True,
                ).start()
        yield

    app = FastAPI(title=f"SeaSwarm {agent_name}", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "agent": agent_name}

    return app
