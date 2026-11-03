"""The Sagar-4 lines the demo posts, and the replies it waits for."""

from __future__ import annotations

AGENTS = ("context", "options", "action")

OVERDUE = (
    "Sagar-4 is overdue by 2 hours and not back. "
    "Missing near the reef, 4 hours of daylight left."
)

STEPS: tuple[tuple[str, str, str], ...] = (
    ("post", "ramesh", OVERDUE),
    ("wait", "context", "@options"),
    ("wait", "context", "0.95"),
    ("wait", "options", "Option A"),
    ("wait", "options", "Option B"),
    ("wait", "options", "Option C"),
    ("wait", "action", "PENDING approval — escalation"),
    ("wait", "action", "2026-02-14"),
    ("wait", "action", "## Operation Sagar-4"),
    ("post", "sunita", "Approved — escalation"),
    ("wait", "action", "Only community_leader can approve escalation."),
    ("post", "ramesh", "Approved — escalation"),
    ("wait", "action", "Released"),
    ("post", "sunita", "photo: https://example.test/reef.jpg"),
    ("wait", "action", "Recorded photo from sunita"),
    ("post", "ramesh", "/audit"),
    ("wait", "action", "Audit written"),
)


def transcript_has(history: list[dict], username: str, snippet: str) -> bool:
    return any(
        item.get("username") == username and snippet in (item.get("text") or "") for item in history
    )
