"""Mattermost poller. Human posts become hub events. Agent posts do not echo."""

from __future__ import annotations

import asyncio
import logging

from agents.common.settings import get_settings
from switch.bootstrap import BridgeState, run_bootstrap
from switch.events import make_event
from switch.mattermost import Mattermost

logger = logging.getLogger(__name__)


def posts_to_events(
    posts: list[dict],
    *,
    room_id: str,
    bot_user_ids: set[str],
    usernames_by_id: dict[str, str],
) -> list[dict]:
    """Translate Mattermost posts into Switch events, dropping bot echoes."""
    events = []
    for post in posts:
        user_id = post.get("user_id", "")
        if user_id in bot_user_ids:
            continue
        if post.get("type"):
            continue
        username = usernames_by_id.get(user_id, post.get("username") or user_id)
        events.append(
            make_event(
                room_id=room_id,
                username=username,
                text=post.get("message", ""),
                message_id=post.get("id"),
                user_id=user_id,
                actor_type="human",
            )
        )
    return events


async def serve_bridge(app) -> None:
    """Retry provisioning, then publish new human posts until cancelled."""
    settings = get_settings()
    delay = 2
    while True:
        mm = Mattermost(settings.mattermost_url)
        try:
            state = await asyncio.to_thread(run_bootstrap, mm, settings)
            app.state.mm = mm
            app.state.bridge_state = state
            app.state.bridge_ready = True
            logger.info("mattermost bridge is ready")
            await _poll(app, mm, state, settings.room_id)
            return
        except asyncio.CancelledError:
            mm.close()
            raise
        except Exception:
            logger.exception("mattermost bridge failed; retrying in %ss", delay)
            mm.close()
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


async def _poll(app, mm: Mattermost, state: BridgeState, room_id: str) -> None:
    seen: set[str] = app.state.seen_post_ids
    try:
        existing = await asyncio.to_thread(
            mm.channel_posts,
            token=state.read_token,
            channel_id=state.channel_id,
        )
        for post in existing:
            if post.get("id"):
                seen.add(post["id"])
        if existing:
            state.since = existing[-1]["id"]
    except Exception:
        logger.exception("could not prime the mattermost cursor")

    while True:
        try:
            posts = await asyncio.to_thread(
                mm.channel_posts,
                token=state.read_token,
                channel_id=state.channel_id,
                since=state.since,
            )
            fresh = []
            newest = state.since
            for post in posts:
                post_id = post.get("id")
                if not post_id or post_id in seen:
                    continue
                seen.add(post_id)
                fresh.append(post)
                newest = post_id
            if newest:
                state.since = newest
            for event in posts_to_events(
                fresh,
                room_id=room_id,
                bot_user_ids=state.bot_user_ids,
                usernames_by_id=state.usernames_by_id,
            ):
                app.state.hub.publish(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("mattermost poll failed")
        await asyncio.sleep(1)
