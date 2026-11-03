"""Load the SAR room template. It holds the demo clock and the role map."""

from __future__ import annotations

from pathlib import Path

import yaml

from agents.common.settings import get_settings


def load_room(path: str | None = None) -> dict:
    template = Path(path or get_settings().room_template)
    return yaml.safe_load(template.read_text())
