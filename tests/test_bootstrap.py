"""Bootstrap provisions the room once and reuses stored tokens."""

from __future__ import annotations

import json

import httpx

from switch.bootstrap import run_bootstrap
from switch.mattermost import Mattermost


class _Settings:
    mattermost_admin_user = "admin"
    mattermost_admin_email = "admin@seaswarm.local"
    mattermost_admin_password = "secret"
    mattermost_team = "seaswarm"
    mattermost_channel = "sar-harnai"
    mattermost_bot_token = ""
    ramesh_password = "ramesh-secret"
    sunita_password = "sunita-secret"
    token_store = ""


def test_bootstrap_creates_people_bots_and_tokens(tmp_path):
    state_box = {"users": {}, "teams": {}, "channels": {}, "tokens": 0, "members": []}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        body = json.loads(request.content.decode() or "{}") if request.content else {}
        if path == "/api/v4/users/login":
            return httpx.Response(200, json={"id": "admin-id"}, headers={"Token": "admin-session"})
        if path == "/api/v4/users" and method == "POST":
            uid = f"id-{body['username']}"
            state_box["users"][body["username"]] = uid
            return httpx.Response(201, json={"id": uid, "username": body["username"]})
        if path.startswith("/api/v4/users/username/"):
            username = path.rsplit("/", 1)[-1]
            uid = state_box["users"].get(username)
            if uid is None:
                return httpx.Response(404, json={"message": "missing"})
            return httpx.Response(200, json={"id": uid, "username": username})
        if path == "/api/v4/teams/name/seaswarm":
            return httpx.Response(404, json={"message": "missing"})
        if path == "/api/v4/teams" and method == "POST":
            state_box["teams"][body["name"]] = "team-1"
            return httpx.Response(201, json={"id": "team-1", "name": body["name"]})
        if path == "/api/v4/teams/team-1/channels/name/sar-harnai":
            return httpx.Response(404, json={"message": "missing"})
        if path == "/api/v4/channels" and method == "POST":
            return httpx.Response(201, json={"id": "chan-1", "name": body["name"]})
        if path == "/api/v4/bots" and method == "POST":
            uid = f"id-{body['username']}"
            state_box["users"][body["username"]] = uid
            return httpx.Response(201, json={"user_id": uid, "username": body["username"]})
        if path.endswith("/members") and method == "POST":
            state_box["members"].append(body["user_id"])
            return httpx.Response(201, json=body)
        if path.endswith("/tokens") and method == "POST":
            state_box["tokens"] += 1
            uid = path.split("/")[4]
            return httpx.Response(200, json={"token": f"token-{uid}-{state_box['tokens']}"})
        return httpx.Response(500, json={"message": f"unhandled {method} {path}"})

    settings = _Settings()
    settings.token_store = str(tmp_path / "tokens.json")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    mm = Mattermost("http://mattermost.test", client=client)
    state = run_bootstrap(mm, settings)

    assert state.channel_id == "chan-1"
    assert state.team_id == "team-1"
    assert set(state.tokens) == {"ramesh", "sunita", "context", "options", "action"}
    assert state.bot_user_ids == {
        state.user_ids["context"],
        state.user_ids["options"],
        state.user_ids["action"],
    }
    assert "ramesh" in state.usernames_by_id[state.user_ids["ramesh"]]
    stored = json.loads((tmp_path / "tokens.json").read_text())
    assert stored["tokens"]["context"] == state.tokens["context"]

    again = run_bootstrap(mm, settings)
    assert again.tokens["context"] == state.tokens["context"]
    assert state_box["tokens"] == 5
