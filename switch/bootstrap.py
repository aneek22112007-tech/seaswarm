"""Provision the Mattermost team, the SAR channel, humans, and agent bots.

The Switch process runs this on startup so `make up` does not need a
hand-created bot token. An existing MATTERMOST_BOT_TOKEN is stored for the
context bot when the operator already has one.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from switch.mattermost import Mattermost, MattermostError, user_id_of

logger = logging.getLogger(__name__)

HUMANS = {
    "ramesh": "ramesh@seaswarm.local",
    "sunita": "sunita@seaswarm.local",
}
BOTS = {
    "context": "Context Agent",
    "options": "Options Agent",
    "action": "Action Agent",
}


@dataclass
class BridgeState:
    channel_id: str
    team_id: str
    tokens: dict[str, str]
    user_ids: dict[str, str]
    bot_user_ids: set[str] = field(default_factory=set)
    usernames_by_id: dict[str, str] = field(default_factory=dict)
    since: str | None = None

    @property
    def read_token(self) -> str:
        return self.tokens["context"]


def load_store(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_store(path: Path, state: BridgeState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "channel_id": state.channel_id,
        "team_id": state.team_id,
        "tokens": state.tokens,
        "user_ids": state.user_ids,
    }
    path.write_text(json.dumps(payload, indent=2))


def _password_for(username: str, settings) -> str:
    if username == "ramesh":
        return settings.ramesh_password
    if username == "sunita":
        return settings.sunita_password
    return settings.mattermost_admin_password


def ensure_login(mm: Mattermost, settings) -> None:
    try:
        mm.login(settings.mattermost_admin_user, settings.mattermost_admin_password)
        return
    except MattermostError:
        logger.info("admin login failed, creating the first user")
    mm.create_user(
        email=settings.mattermost_admin_email,
        username=settings.mattermost_admin_user,
        password=settings.mattermost_admin_password,
    )
    mm.login(settings.mattermost_admin_user, settings.mattermost_admin_password)


def ensure_human(mm: Mattermost, username: str, email: str, password: str) -> dict:
    existing = mm.get_user_by_username(username)
    if existing:
        return existing
    return mm.create_user(email=email, username=username, password=password)


def ensure_bot(mm: Mattermost, username: str, display_name: str) -> dict:
    existing = mm.get_user_by_username(username)
    if existing:
        return existing
    created = mm.create_bot(username=username, display_name=display_name)
    return {"id": user_id_of(created), "username": username}


def ensure_team(mm: Mattermost, name: str, display_name: str) -> dict:
    existing = mm.get_team_by_name(name)
    if existing:
        return existing
    return mm.create_team(name=name, display_name=display_name)


def ensure_channel(mm: Mattermost, team_id: str, name: str, display_name: str) -> dict:
    existing = mm.get_channel_by_name(team_id, name)
    if existing:
        return existing
    return mm.create_channel(team_id=team_id, name=name, display_name=display_name)


def run_bootstrap(mm: Mattermost, settings) -> BridgeState:
    """Create the demo room if needed and return tokens for every speaker."""
    store_path = Path(settings.token_store)
    stored = load_store(store_path) or {}
    stored_tokens = dict(stored.get("tokens") or {})

    ensure_login(mm, settings)
    team = ensure_team(mm, settings.mattermost_team, "SeaSwarm")
    channel = ensure_channel(mm, team["id"], settings.mattermost_channel, "Harnai SAR")

    user_ids: dict[str, str] = {}
    tokens: dict[str, str] = {}

    for username, email in HUMANS.items():
        record = ensure_human(mm, username, email, _password_for(username, settings))
        uid = user_id_of(record)
        user_ids[username] = uid
        mm.add_team_member(team["id"], uid)
        mm.add_channel_member(channel["id"], uid)
        tokens[username] = stored_tokens.get(username) or mm.create_token(uid, "seaswarm-demo")

    provided = (settings.mattermost_bot_token or "").strip()
    for username, display_name in BOTS.items():
        record = ensure_bot(mm, username, display_name)
        uid = user_id_of(record)
        user_ids[username] = uid
        mm.add_team_member(team["id"], uid)
        mm.add_channel_member(channel["id"], uid)
        if username == "context" and provided:
            tokens[username] = provided
        else:
            tokens[username] = stored_tokens.get(username) or mm.create_token(
                uid, "seaswarm-switch"
            )

    state = BridgeState(
        channel_id=channel["id"],
        team_id=team["id"],
        tokens=tokens,
        user_ids=user_ids,
        bot_user_ids={user_ids[name] for name in BOTS},
        usernames_by_id={uid: name for name, uid in user_ids.items()},
    )
    save_store(store_path, state)
    logger.info("switch bridge ready for channel %s", channel["id"])
    return state
