"""Telegram and Discord messages become room lines only when the flag is on."""

from __future__ import annotations

from fastapi.testclient import TestClient

from adapters.gateway import app, discord_text, telegram_text


def test_telegram_update_keeps_the_username_and_text():
    parsed = telegram_text(
        {"message": {"text": " Sagar-4 is overdue ", "from": {"username": "ramesh"}}}
    )
    assert parsed == ("ramesh", "Sagar-4 is overdue")
    assert telegram_text({"message": {"text": "hello"}}) is None


def test_discord_message_skips_bots():
    assert discord_text({"author": {"username": "sunita"}, "content": "note: home"}) == (
        "sunita",
        "note: home",
    )
    assert discord_text({"author": {"username": "bot", "bot": True}, "content": "hi"}) is None


def test_disabled_doors_do_not_forward():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["telegram"] is False
        assert health.json()["discord"] is False
        telegram = client.post(
            "/telegram",
            json={"message": {"text": "overdue", "from": {"username": "ramesh"}}},
        )
        discord = client.post(
            "/discord",
            json={"author": {"username": "sunita"}, "content": "Approved — scheme-outreach"},
        )
    assert telegram.json()["forwarded"] is False
    assert discord.json()["forwarded"] is False


def test_enabled_telegram_forwards_one_line(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "adapters.gateway.forward", lambda username, text: seen.append((username, text))
    )
    with TestClient(app) as client:
        response = client.post(
            "/telegram",
            json={"message": {"text": "Sagar-4 is overdue", "from": {"username": "ramesh"}}},
        )
    assert response.json()["forwarded"] is True
    assert seen == [("ramesh", "Sagar-4 is overdue")]
