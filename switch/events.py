"""Event envelopes shared by the hub, the bridge, and the agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

AGENT_USERNAMES = frozenset({"context", "options", "action", "echo"})


def actor_type_for(username: str) -> str:
    if username in AGENT_USERNAMES:
        return "agent"
    return "human"


def make_event(
    *,
    room_id: str,
    username: str,
    text: str,
    actor_type: str | None = None,
    message_id: str | None = None,
    user_id: str = "",
) -> dict:
    """Build one room event. Message ids are stable so replies can be updated."""
    mid = message_id or uuid.uuid4().hex
    return {
        "id": mid,
        "message_id": mid,
        "room_id": room_id,
        "user_id": user_id,
        "username": username,
        "text": text,
        "actor_type": actor_type or actor_type_for(username),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
