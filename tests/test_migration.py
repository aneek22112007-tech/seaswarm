"""The hand-written migration matches the SQLAlchemy metadata."""

from __future__ import annotations

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from agents.common.models import Base
from alembic import command
from tests.conftest import ROOT


def test_upgrade_creates_every_model_table(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    names = set(inspect(engine).get_table_names()) - {"alembic_version"}
    engine.dispose()
    assert names == set(Base.metadata.tables)
