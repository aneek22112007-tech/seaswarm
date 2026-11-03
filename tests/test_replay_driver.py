"""The replay driver posts the human lines and waits for the scripted replies."""

from __future__ import annotations

from scripts.replay_demo import play
from scripts.scenario import OVERDUE


class _Scripted:
    def __init__(self) -> None:
        self.posts: list[tuple[str, str]] = []
        self.items: list[dict] = []

    def subscribers(self) -> list[str]:
        return ["context", "options", "action"]

    def history(self) -> list[dict]:
        return list(self.items)

    def post_human(self, username: str, text: str) -> dict:
        self.posts.append((username, text))
        self.items.append({"username": username, "actor_type": "human", "text": text})
        self.items.extend(_canned(username, text))
        return {"message_id": f"m-{len(self.posts)}"}


def _canned(username: str, text: str) -> list[dict]:
    if "overdue" in text:
        return [
            {"username": "context", "text": "radius 0.95 km\n@options"},
            {"username": "options", "text": "Option A\nOption B\nOption C"},
            {
                "username": "action",
                "text": "PENDING approval — escalation\n2026-02-14\n## Operation Sagar-4",
            },
        ]
    if username == "sunita" and text.startswith("Approved"):
        return [{"username": "action", "text": "Only community_leader can approve escalation."}]
    if username == "ramesh" and text.startswith("Approved"):
        return [{"username": "action", "text": "Released approval:1 escalation"}]
    if text.startswith("photo:"):
        return [
            {
                "username": "action",
                "text": "Recorded photo from sunita: https://example.test/reef.jpg",
            }
        ]
    if text == "/audit":
        return [{"username": "action", "text": "Audit written to audit.md and audit.pdf."}]
    return []


def test_driver_walks_the_sagar_4_steps(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    client = _Scripted()
    history = play(client, timeout=2, sleep=lambda _seconds: None, do_seed=False)
    assert client.posts[0] == ("ramesh", OVERDUE)
    assert ("sunita", "Approved — escalation") in client.posts
    assert ("ramesh", "/audit") in client.posts
    assert any("Released" in item["text"] for item in history if item["username"] == "action")
