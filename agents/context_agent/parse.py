"""Pull a boat name and the two clocks out of a human message."""

from __future__ import annotations

import re

TRIGGERS = ("overdue", "sos", "not back", "missing")
OVERDUE_RE = re.compile(r"overdue(?:\s+by)?\s+(\d+(?:\.\d+)?)\s+hours?")
DAYLIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s+hours?\s+of\s+daylight")


def is_trigger(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in TRIGGERS)


def parse_overdue_hours(text: str) -> float | None:
    match = OVERDUE_RE.search(text.lower())
    if not match:
        return None
    return float(match.group(1))


def parse_daylight_hours(text: str) -> float | None:
    match = DAYLIGHT_RE.search(text.lower())
    if not match:
        return None
    return float(match.group(1))


def boat_from_text(text: str, catalog: list[dict]) -> dict | None:
    lowered = text.lower()
    ordered = sorted(catalog, key=lambda item: len(item["name"]), reverse=True)
    for boat in ordered:
        if boat["name"].lower() in lowered:
            return boat
    return None
