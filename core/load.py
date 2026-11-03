"""Read the mock JSON registers. Paths come from DATA_DIR or the repo data folder."""

from __future__ import annotations

import json
import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    return Path(os.getenv("DATA_DIR") or (repo_root() / "data"))


def load_json(name: str) -> dict:
    path = data_dir() / name
    return json.loads(path.read_text())
