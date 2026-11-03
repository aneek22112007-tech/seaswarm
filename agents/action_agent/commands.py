"""Room lines the action agent acts on, besides sign-off phrases."""

from __future__ import annotations

import re

CLOSE_RE = re.compile(r"\bclose (?:the )?search\b", re.IGNORECASE)


def is_mention(text: str) -> bool:
    return "@action" in text.lower()


def wants_close(text: str) -> bool:
    return CLOSE_RE.search(text) is not None


def is_audit(text: str) -> bool:
    return text.strip() == "/audit"
