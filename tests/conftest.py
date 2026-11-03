"""Keep the suite offline and pointed at the repo fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

os.environ["LLM_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = ""
os.environ["SWITCH_BRIDGE"] = "off"
os.environ["SEASWARM_SEED"] = "42"
os.environ["PERSISTENCE"] = "on"
os.environ["DATA_DIR"] = str(ROOT / "data")
os.environ["ROOM_TEMPLATE"] = str(ROOT / "room_templates" / "sar_room.yaml")
os.environ["SWITCH_TOKEN"] = "test-token"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SEASWARM_DISABLE_LOOP"] = "1"
os.environ["TOKEN_STORE"] = str(ROOT / ".runtime" / "mm_tokens.json")


@pytest.fixture
def engine(tmp_path):
    from agents.common.db import make_engine
    from agents.common.models import Base

    database = make_engine(f"sqlite:///{tmp_path / 'seaswarm.db'}")
    Base.metadata.create_all(database)
    yield database
    database.dispose()


@pytest.fixture
def session(engine):
    from agents.common.db import session_factory

    bound = session_factory(engine)()
    yield bound
    bound.close()
