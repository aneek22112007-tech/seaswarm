"""Optional Telegram and Discord doors into the same Switch room.

Both stay idle unless TELEGRAM_ENABLED or DISCORD_ENABLED is set. A disabled
door acknowledges the payload and does not post into the room.
"""

from __future__ import annotations

from fastapi import FastAPI

from agents.common.settings import get_settings
from agents.common.switch_client import SwitchClient


def telegram_text(update: dict) -> tuple[str, str] | None:
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    sender = message.get("from") or {}
    username = (sender.get("username") or "").strip()
    if not text or not username:
        return None
    return username, text


def discord_text(payload: dict) -> tuple[str, str] | None:
    author = payload.get("author") or {}
    username = (author.get("username") or "").strip()
    text = (payload.get("content") or "").strip()
    if not text or not username or author.get("bot"):
        return None
    return username, text


def forward(username: str, text: str) -> None:
    client = SwitchClient(agent="adapter")
    try:
        client.post_human(username, text)
    finally:
        client.close()


app = FastAPI(title="SeaSwarm adapters")


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "ok": True,
        "telegram": settings.telegram_enabled,
        "discord": settings.discord_enabled,
    }


@app.post("/telegram")
def telegram(update: dict) -> dict:
    if not get_settings().telegram_enabled:
        return {"ok": True, "forwarded": False}
    parsed = telegram_text(update)
    if parsed is None:
        return {"ok": True, "forwarded": False}
    forward(*parsed)
    return {"ok": True, "forwarded": True}


@app.post("/discord")
def discord(payload: dict) -> dict:
    if not get_settings().discord_enabled:
        return {"ok": True, "forwarded": False}
    parsed = discord_text(payload)
    if parsed is None:
        return {"ok": True, "forwarded": False}
    forward(*parsed)
    return {"ok": True, "forwarded": True}
