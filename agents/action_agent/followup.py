"""When the next check-in is due. The clock is pure; the loop only posts."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from agents.common.room import load_room
from agents.common.settings import get_settings
from agents.common.store import find_open_operation, list_events, persistence_enabled, record_event
from core.load import load_json

logger = logging.getLogger(__name__)


def next_followup(now: datetime, interval_seconds: int) -> datetime:
    if interval_seconds <= 0:
        raise ValueError("follow-up interval must be positive")
    return now + timedelta(seconds=interval_seconds)


def followup_due(now: datetime, last: datetime | None, interval_seconds: int) -> bool:
    if last is None:
        return False
    return _aware(now) >= _aware(last) + timedelta(seconds=interval_seconds)


def render_followup(boat_name: str, due_at: datetime) -> str:
    stamp = _aware(due_at).strftime("%H:%M")
    return (
        f"Follow-up for {boat_name}: the search is still open at {stamp}. "
        "Reply with sector clears, evidence, or a sign-off. "
        "Nothing is sent outside this room."
    )


def post_if_due(session, client, now: datetime) -> str | None:
    """Post one follow-up when the interval has elapsed. Returns the text, or None."""
    if not persistence_enabled():
        return None
    room = load_room()
    operation = find_open_operation(session, room["boat_id"])
    if operation is None or operation.status in {"found", "closed"}:
        return None
    interval = get_settings().followup_interval_seconds
    previous = list_events(session, operation.id, kind="followup")
    anchor = previous[-1].created_at if previous else operation.opened_at
    if not followup_due(now, anchor, interval):
        return None
    boats = {boat["id"]: boat for boat in load_json("boats.json")["boats"]}
    boat_name = boats.get(room["boat_id"], {}).get("name", room["boat_id"])
    text = render_followup(boat_name, now)
    client.post(text)
    record_event(
        session,
        op_id=operation.id,
        actor="action",
        actor_type="agent",
        kind="followup",
        body=text,
        created_at=_aware(now),
    )
    return text


def followup_loop(sleep=time.sleep, client_factory=None) -> None:
    """Wait one interval, then post if a search is still open. Repeats until stopped."""
    from agents.common.db import init_db, session_scope
    from agents.common.switch_client import SwitchClient

    factory = client_factory or (lambda: SwitchClient(agent="action"))
    while True:
        sleep(get_settings().followup_interval_seconds)
        try:
            client = factory()
            engine = init_db()
            with session_scope(engine) as session:
                post_if_due(session, client, datetime.now(timezone.utc))
        except Exception:
            logger.exception("follow-up failed")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
