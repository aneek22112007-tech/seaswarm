"""Switch HTTP API.

Agents subscribe with GET /v1/events (SSE) and speak with POST /v1/rooms/{id}/messages.
The console is served at /.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from switch.bridge import serve_bridge
from switch.events import make_event
from switch.hub import Hub

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class MessageIn(BaseModel):
    agent: str
    text: str
    pin: bool = False
    root_id: str | None = None


class HumanIn(BaseModel):
    username: str
    text: str


class EditIn(BaseModel):
    agent: str
    text: str = Field(min_length=1)


def assert_token(request: Request) -> None:
    expected = os.getenv("SWITCH_TOKEN", "seaswarm-dev-token")
    provided = request.headers.get("x-switch-token", "")
    if provided != expected:
        raise HTTPException(status_code=401, detail="invalid switch token")


def create_app(*, enable_bridge: bool | None = None) -> FastAPI:
    if enable_bridge is None:
        from agents.common.settings import get_settings

        enable_bridge = get_settings().bridge_enabled

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.bridge_task = None
        if enable_bridge:
            app.state.bridge_task = asyncio.create_task(serve_bridge(app))
        yield
        task = app.state.bridge_task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="SeaSwarm Switch", lifespan=lifespan)
    app.state.hub = Hub()
    app.state.bridge_ready = not enable_bridge
    app.state.mm = None
    app.state.bridge_state = None
    app.state.bridge_enabled = enable_bridge
    app.state.seen_post_ids = set()

    @app.get("/health")
    def health():
        if enable_bridge and not app.state.bridge_ready:
            raise HTTPException(status_code=503, detail="bridge starting")
        return {"ok": True, "service": "switch", "bridge": bool(app.state.bridge_ready)}

    @app.get("/")
    def console():
        page = STATIC_DIR / "console.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="console is not installed")
        return FileResponse(page)

    @app.get("/v1/rooms/{room_id}/history")
    def history(room_id: str):
        return app.state.hub.history(room_id)

    @app.get("/v1/events")
    async def events(room_id: str, agent: str = "console"):
        queue = app.state.hub.subscribe(room_id)
        logger.info("sse subscribe room=%s agent=%s", room_id, agent)

        async def generate():
            try:
                yield ": connected\n\n"
                while True:
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
                        continue
                    yield "data: " + json.dumps(item) + "\n\n"
            finally:
                app.state.hub.unsubscribe(queue)

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/v1/rooms/{room_id}/messages")
    def post_message(room_id: str, body: MessageIn, request: Request):
        assert_token(request)
        event = _deliver_agent(app, room_id, body)
        return {"message_id": event["message_id"]}

    @app.post("/v1/rooms/{room_id}/human")
    def post_human(room_id: str, body: HumanIn, request: Request):
        assert_token(request)
        event = _deliver_human(app, room_id, body)
        return {"message_id": event["message_id"]}

    @app.put("/v1/rooms/{room_id}/messages/{message_id}")
    def edit_message(room_id: str, message_id: str, body: EditIn, request: Request):
        assert_token(request)
        updated = _edit(app, room_id, message_id, body)
        if updated is None:
            raise HTTPException(status_code=404, detail="message not found")
        return updated

    return app


def _token_for(app: FastAPI, username: str) -> str | None:
    state = app.state.bridge_state
    if state is None:
        return None
    return state.tokens.get(username)


def _deliver_agent(app: FastAPI, room_id: str, body: MessageIn) -> dict:
    message_id = None
    state = app.state.bridge_state
    mm = app.state.mm
    if state is not None and mm is not None:
        token = state.tokens[body.agent]
        posted = mm.create_post(
            token=token,
            channel_id=state.channel_id,
            message=body.text,
            root_id=body.root_id,
        )
        message_id = posted["id"]
        app.state.seen_post_ids.add(message_id)
        if body.pin:
            mm.pin_post(token=token, post_id=message_id)
    event = make_event(
        room_id=room_id,
        username=body.agent,
        text=body.text,
        actor_type="agent",
        message_id=message_id,
    )
    return app.state.hub.publish(event)


def _deliver_human(app: FastAPI, room_id: str, body: HumanIn) -> dict:
    message_id = None
    user_id = ""
    state = app.state.bridge_state
    mm = app.state.mm
    if state is not None and mm is not None:
        token = _token_for(app, body.username)
        if not token:
            raise HTTPException(status_code=404, detail=f"unknown speaker {body.username}")
        posted = mm.create_post(token=token, channel_id=state.channel_id, message=body.text)
        message_id = posted["id"]
        user_id = state.user_ids.get(body.username, "")
        app.state.seen_post_ids.add(message_id)
    event = make_event(
        room_id=room_id,
        username=body.username,
        text=body.text,
        actor_type="human",
        message_id=message_id,
        user_id=user_id,
    )
    return app.state.hub.publish(event)


def _edit(app: FastAPI, room_id: str, message_id: str, body: EditIn) -> dict | None:
    state = app.state.bridge_state
    mm = app.state.mm
    if state is not None and mm is not None:
        token = state.tokens[body.agent]
        mm.update_post(token=token, post_id=message_id, message=body.text)
    return app.state.hub.update(room_id, message_id, body.text)


app = create_app()
