"""Mattermost payload builders and the HTTP client against a fake transport."""

from __future__ import annotations

import httpx

from switch.bridge import posts_to_events
from switch.mattermost import (
    Mattermost,
    channel_body,
    post_body,
    user_id_of,
)


def test_post_body_can_thread_a_reply():
    body = post_body(channel_id="chan", message="Approved", root_id="root")
    assert body == {"channel_id": "chan", "message": "Approved", "root_id": "root"}


def test_channel_body_is_a_public_channel():
    body = channel_body(team_id="team", name="sar-harnai", display_name="Harnai SAR")
    assert body["type"] == "O"
    assert body["name"] == "sar-harnai"


def test_user_id_of_accepts_bot_and_user_records():
    assert user_id_of({"user_id": "bot-1"}) == "bot-1"
    assert user_id_of({"id": "user-1"}) == "user-1"


def test_login_stores_the_session_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v4/users/login"
        return httpx.Response(200, json={"id": "admin"}, headers={"Token": "session-1"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    mm = Mattermost("http://mattermost.test", client=client)
    assert mm.login("admin", "secret") == "session-1"
    assert mm.token == "session-1"


def test_create_post_sends_the_bearer_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read()
        return httpx.Response(201, json={"id": "post-9"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    mm = Mattermost("http://mattermost.test", client=client)
    posted = mm.create_post(token="bot-token", channel_id="chan", message="cone")
    assert posted["id"] == "post-9"
    assert seen["auth"] == "Bearer bot-token"


def test_channel_posts_are_returned_oldest_first():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["since"] == "p1"
        return httpx.Response(
            200,
            json={
                "order": ["p3", "p2"],
                "posts": {
                    "p2": {"id": "p2", "message": "second", "user_id": "u"},
                    "p3": {"id": "p3", "message": "third", "user_id": "u"},
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    mm = Mattermost("http://mattermost.test", client=client)
    posts = mm.channel_posts(token="t", channel_id="chan", since="p1")
    assert [post["id"] for post in posts] == ["p2", "p3"]


def test_bot_posts_do_not_become_events():
    posts = [
        {"id": "1", "user_id": "bot", "message": "summary"},
        {"id": "2", "user_id": "human", "message": "Sagar-4 is overdue"},
        {"id": "3", "user_id": "human", "message": "joined", "type": "system_join_channel"},
    ]
    events = posts_to_events(
        posts,
        room_id="sar-harnai",
        bot_user_ids={"bot"},
        usernames_by_id={"human": "ramesh"},
    )
    assert len(events) == 1
    assert events[0]["username"] == "ramesh"
    assert events[0]["text"] == "Sagar-4 is overdue"
    assert events[0]["actor_type"] == "human"
