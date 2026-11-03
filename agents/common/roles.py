"""Map a Mattermost username to the role that may sign the audit trail."""

from __future__ import annotations

from agents.common.room import load_room

DEFAULT_ROLES = {
    "ramesh": "community_leader",
    "sunita": "family_rep",
    "admin": "community_leader",
}


def role_map() -> dict[str, str]:
    try:
        loaded = load_room().get("roles") or {}
    except (OSError, KeyError, TypeError):
        loaded = {}
    return {**DEFAULT_ROLES, **loaded}


def role_for(username: str, mapping: dict[str, str] | None = None) -> str | None:
    return (mapping or role_map()).get(username)
