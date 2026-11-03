"""Post the Sagar-4 scenario into the room and wait for each agent reply."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.common.switch_client import SwitchClient  # noqa: E402
from scripts.scenario import AGENTS, STEPS, transcript_has  # noqa: E402
from scripts.seed_demo import seed_database  # noqa: E402


def play(client, *, timeout: float = 90, sleep=time.sleep, do_seed: bool = True) -> list[dict]:
    if do_seed:
        print(seed_database())
    _wait(
        client,
        lambda: set(AGENTS) <= set(client.subscribers()),
        timeout,
        sleep,
        "agents " + ", ".join(AGENTS),
    )
    for kind, username, text in STEPS:
        if kind == "post":
            client.post_human(username, text)
            print(f"> {username}: {text}")
            continue
        _wait(
            client,
            lambda username=username, text=text: transcript_has(client.history(), username, text),
            timeout,
            sleep,
            f"{username} saying {text}",
        )
        print(f"< {username} has {text}")
    return client.history()


def _wait(client, predicate, timeout: float, sleep, label: str) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if predicate():
                return
        except Exception:
            pass
        sleep(1)
    history = _safe_history(client)
    tail = "\n".join(f"{item.get('username')}: {item.get('text')}" for item in history[-12:])
    raise SystemExit(f"timed out waiting for {label}\n{tail}")


def _safe_history(client) -> list[dict]:
    try:
        return list(client.history())
    except Exception:
        return []


def main() -> None:
    client = SwitchClient(agent="demo")
    try:
        play(client)
    finally:
        client.close()
    print("Sagar-4 scenario complete")


if __name__ == "__main__":
    main()
