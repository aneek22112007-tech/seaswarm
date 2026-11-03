"""Repeat a human line that starts with 'echo '. Other room traffic is left alone."""

from __future__ import annotations


def handle_event(event: dict) -> str | None:
    if event.get("actor_type") != "human":
        return None
    text = (event.get("text") or "").strip()
    if not text.lower().startswith("echo "):
        return None
    return f"echo: {text[5:].strip()}"
