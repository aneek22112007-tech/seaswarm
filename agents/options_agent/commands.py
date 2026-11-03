"""Room commands that make the options agent re-plan."""

from __future__ import annotations

import re
from dataclasses import dataclass

CLEAR_RE = re.compile(r"sector[-\s]?(\d+)\s+clear", re.IGNORECASE)
REASSIGN_RE = re.compile(
    r"reassign\s+([A-Za-z0-9_-]+)\s+to\s+sector[-\s]?(\d+)",
    re.IGNORECASE,
)
REJECT_RE = re.compile(r"reject\s+option\s+([A-C])", re.IGNORECASE)


@dataclass(frozen=True)
class Command:
    kind: str
    sector: str | None = None
    boat: str | None = None
    option_id: str | None = None


def parse_command(text: str, actor_type: str) -> Command | None:
    if actor_type == "human":
        clear = CLEAR_RE.search(text)
        if clear:
            return Command(kind="clear", sector=f"Sector-{clear.group(1)}")
        reassign = REASSIGN_RE.search(text)
        if reassign:
            return Command(
                kind="reassign",
                boat=reassign.group(1),
                sector=f"Sector-{reassign.group(2)}",
            )
        reject = REJECT_RE.search(text)
        if reject:
            return Command(kind="reject", option_id=reject.group(1).upper())
    if "@options" in text.lower():
        return Command(kind="plan")
    return None
