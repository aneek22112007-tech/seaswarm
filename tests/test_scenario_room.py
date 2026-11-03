"""The three agents carry Sagar-4 from the overdue report through the audit."""

from __future__ import annotations

from agents.action_agent.handler import handle_event as action_handle
from agents.context_agent.handler import handle_event as context_handle
from agents.options_agent.handler import handle_event as options_handle
from scripts.scenario import STEPS, transcript_has
from scripts.seed_demo import seed_database

HANDLERS = {
    "context": context_handle,
    "options": options_handle,
    "action": action_handle,
}


def _fanout(history: list[dict], event: dict) -> None:
    pending = [event]
    history.append(event)
    steps = 0
    while pending and steps < 40:
        steps += 1
        current = pending.pop(0)
        for name, handler in HANDLERS.items():
            if current.get("username") == name:
                continue
            reply = handler(current)
            texts: list[str] = []
            if isinstance(reply, str):
                texts = [reply]
            elif isinstance(reply, list):
                texts = [item for item in reply if isinstance(item, str) and item.strip()]
            for text in texts:
                nxt = {
                    "username": name,
                    "actor_type": "agent",
                    "text": text,
                    "message_id": f"m-{len(history)}",
                }
                history.append(nxt)
                pending.append(nxt)


def test_sagar_4_runs_from_report_to_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'room.db'}")
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("PERSISTENCE", "on")
    monkeypatch.setenv("LLM_API_KEY", "")
    seed_database()
    history: list[dict] = []
    for kind, username, text in STEPS:
        if kind == "post":
            _fanout(
                history,
                {
                    "username": username,
                    "actor_type": "human",
                    "text": text,
                    "message_id": f"m-{len(history)}",
                },
            )
            continue
        assert transcript_has(history, username, text), _dump(history, username, text)
    joined = "\n".join(item["text"] for item in history)
    assert "Only community_leader can approve escalation." in joined
    assert "Released" in joined
    assert any(path.suffix == ".pdf" for path in (tmp_path / "exports").iterdir())


def _dump(history: list[dict], username: str, text: str) -> str:
    body = "\n".join(f"{item['username']}: {item['text'][:180]}" for item in history)
    return f"missing {username!r} {text!r}\n{body}"
