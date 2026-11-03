"""Switch HTTP routes without a Mattermost bridge."""

from __future__ import annotations

from fastapi.testclient import TestClient

from switch.server import create_app

TOKEN = {"X-Switch-Token": "test-token"}


def _client() -> TestClient:
    return TestClient(create_app(enable_bridge=False))


def test_subscribers_route_is_empty_without_a_listener():
    with _client() as client:
        response = client.get("/v1/rooms/sar-harnai/subscribers")
        assert response.status_code == 200
        assert response.json() == {"agents": []}


def test_health_is_ready_when_the_bridge_is_off():
    with _client() as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "switch"


def test_agent_post_requires_the_switch_token():
    with _client() as client:
        rejected = client.post(
            "/v1/rooms/sar-harnai/messages",
            json={"agent": "context", "text": "hello"},
        )
        assert rejected.status_code == 401
        accepted = client.post(
            "/v1/rooms/sar-harnai/messages",
            json={"agent": "context", "text": "Sagar-4 summary"},
            headers=TOKEN,
        )
        assert accepted.status_code == 200
        history = client.get("/v1/rooms/sar-harnai/history").json()
        assert history[0]["username"] == "context"
        assert history[0]["actor_type"] == "agent"
        assert "Sagar-4" in history[0]["text"]


def test_human_post_and_edit_round_trip():
    with _client() as client:
        created = client.post(
            "/v1/rooms/sar-harnai/human",
            json={"username": "ramesh", "text": "Sagar-4 is overdue"},
            headers=TOKEN,
        )
        message_id = created.json()["message_id"]
        edited = client.put(
            f"/v1/rooms/sar-harnai/messages/{message_id}",
            json={"agent": "action", "text": "checklist v2"},
            headers=TOKEN,
        )
        assert edited.status_code == 200
        history = client.get("/v1/rooms/sar-harnai/history").json()
        assert history[0]["text"] == "checklist v2"


def test_console_page_is_served():
    with _client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "SeaSwarm Switch" in response.text
