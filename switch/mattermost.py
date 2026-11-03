"""Small Mattermost client for the Switch bridge.

The bridge logs in as the demo admin, provisions the room, and posts as the
agent bots. Payload builders stay pure so tests do not need a server.
"""

from __future__ import annotations

import httpx


class MattermostError(RuntimeError):
    """Raised when Mattermost rejects a call the bridge cannot continue without."""


def login_body(login_id: str, password: str) -> dict:
    return {"login_id": login_id, "password": password}


def user_body(*, email: str, username: str, password: str) -> dict:
    return {"email": email, "username": username, "password": password}


def team_body(*, name: str, display_name: str) -> dict:
    return {"name": name, "display_name": display_name, "type": "O"}


def channel_body(*, team_id: str, name: str, display_name: str) -> dict:
    return {"team_id": team_id, "name": name, "display_name": display_name, "type": "O"}


def bot_body(*, username: str, display_name: str) -> dict:
    return {
        "username": username,
        "display_name": display_name,
        "description": "SeaSwarm agent",
    }


def post_body(*, channel_id: str, message: str, root_id: str | None = None) -> dict:
    body = {"channel_id": channel_id, "message": message}
    if root_id:
        body["root_id"] = root_id
    return body


def user_id_of(record: dict) -> str:
    """Bot records use user_id. User records use id."""
    return str(record.get("user_id") or record["id"])


class Mattermost:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=30.0)
        self.token = ""

    def close(self) -> None:
        self.client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        headers = {}
        use = self.token if token is None else token
        if use:
            headers["Authorization"] = f"Bearer {use}"
        return self.client.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            json=json,
            params=params,
        )

    def login(self, login_id: str, password: str) -> str:
        response = self._request(
            "POST",
            "/api/v4/users/login",
            json=login_body(login_id, password),
        )
        if response.status_code >= 400:
            raise MattermostError(f"login failed: {response.status_code} {response.text}")
        token = response.headers.get("Token", "")
        if not token:
            raise MattermostError("login response did not include a token")
        self.token = token
        return token

    def create_user(self, *, email: str, username: str, password: str) -> dict:
        response = self._request(
            "POST",
            "/api/v4/users",
            json=user_body(email=email, username=username, password=password),
        )
        if response.status_code >= 400:
            raise MattermostError(f"create user failed: {response.status_code} {response.text}")
        return response.json()

    def get_user_by_username(self, username: str) -> dict | None:
        response = self._request("GET", f"/api/v4/users/username/{username}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise MattermostError(f"get user failed: {response.status_code} {response.text}")
        return response.json()

    def create_token(self, user_id: str, description: str) -> str:
        response = self._request(
            "POST",
            f"/api/v4/users/{user_id}/tokens",
            json={"description": description},
        )
        if response.status_code >= 400:
            raise MattermostError(f"create token failed: {response.status_code} {response.text}")
        return str(response.json()["token"])

    def get_team_by_name(self, name: str) -> dict | None:
        response = self._request("GET", f"/api/v4/teams/name/{name}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise MattermostError(f"get team failed: {response.status_code} {response.text}")
        return response.json()

    def create_team(self, *, name: str, display_name: str) -> dict:
        response = self._request(
            "POST",
            "/api/v4/teams",
            json=team_body(name=name, display_name=display_name),
        )
        if response.status_code >= 400:
            raise MattermostError(f"create team failed: {response.status_code} {response.text}")
        return response.json()

    def get_channel_by_name(self, team_id: str, name: str) -> dict | None:
        response = self._request("GET", f"/api/v4/teams/{team_id}/channels/name/{name}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise MattermostError(f"get channel failed: {response.status_code} {response.text}")
        return response.json()

    def create_channel(self, *, team_id: str, name: str, display_name: str) -> dict:
        response = self._request(
            "POST",
            "/api/v4/channels",
            json=channel_body(team_id=team_id, name=name, display_name=display_name),
        )
        if response.status_code >= 400:
            raise MattermostError(f"create channel failed: {response.status_code} {response.text}")
        return response.json()

    def add_member(self, path: str, payload: dict) -> None:
        response = self._request("POST", path, json=payload)
        if response.status_code in (200, 201):
            return
        text = response.text.lower()
        if response.status_code == 400 and "already" in text:
            return
        if response.status_code >= 400:
            raise MattermostError(f"add member failed: {response.status_code} {response.text}")

    def add_team_member(self, team_id: str, user_id: str) -> None:
        self.add_member(
            f"/api/v4/teams/{team_id}/members",
            {"team_id": team_id, "user_id": user_id},
        )

    def add_channel_member(self, channel_id: str, user_id: str) -> None:
        self.add_member(f"/api/v4/channels/{channel_id}/members", {"user_id": user_id})

    def create_bot(self, *, username: str, display_name: str) -> dict:
        response = self._request(
            "POST",
            "/api/v4/bots",
            json=bot_body(username=username, display_name=display_name),
        )
        if response.status_code >= 400:
            raise MattermostError(f"create bot failed: {response.status_code} {response.text}")
        return response.json()

    def create_post(
        self,
        *,
        token: str,
        channel_id: str,
        message: str,
        root_id: str | None = None,
    ) -> dict:
        response = self._request(
            "POST",
            "/api/v4/posts",
            token=token,
            json=post_body(channel_id=channel_id, message=message, root_id=root_id),
        )
        if response.status_code >= 400:
            raise MattermostError(f"create post failed: {response.status_code} {response.text}")
        return response.json()

    def update_post(self, *, token: str, post_id: str, message: str) -> dict:
        response = self._request(
            "PUT",
            f"/api/v4/posts/{post_id}",
            token=token,
            json={"id": post_id, "message": message},
        )
        if response.status_code >= 400:
            raise MattermostError(f"update post failed: {response.status_code} {response.text}")
        return response.json()

    def pin_post(self, *, token: str, post_id: str) -> None:
        response = self._request("POST", f"/api/v4/posts/{post_id}/pin", token=token)
        if response.status_code >= 400:
            raise MattermostError(f"pin failed: {response.status_code} {response.text}")

    def channel_posts(
        self,
        *,
        token: str,
        channel_id: str,
        since: str | None = None,
    ) -> list[dict]:
        params: dict[str, str | int] = {"since": since} if since else {"page": 0, "per_page": 100}
        response = self._request(
            "GET",
            f"/api/v4/channels/{channel_id}/posts",
            token=token,
            params=params,
        )
        if response.status_code >= 400:
            raise MattermostError(f"list posts failed: {response.status_code} {response.text}")
        payload = response.json()
        posts = payload.get("posts", {})
        order = payload.get("order", [])
        return [posts[post_id] for post_id in reversed(order) if post_id in posts]
