"""Mattermost usernames map to the roles that can sign off."""

from __future__ import annotations

from agents.common.roles import role_for


def test_known_demo_roles():
    assert role_for("ramesh") == "community_leader"
    assert role_for("sunita") == "family_rep"
    assert role_for("stranger") is None


def test_explicit_map_overrides_the_room():
    assert role_for("sunita", {"sunita": "community_leader"}) == "community_leader"
