"""Runtime configuration. Process environment wins. Compose injects `.env`."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    seaswarm_seed: int = 42
    persistence: str = "on"
    database_url: str = "sqlite:///./.runtime/seaswarm.db"
    data_dir: str = "data"
    export_dir: str = "./.runtime/exports"
    room_template: str = "room_templates/sar_room.yaml"

    switch_url: str = "http://localhost:8090"
    switch_port: int = 8090
    switch_token: str = "seaswarm-dev-token"
    switch_bridge: str = "off"
    room_id: str = "sar-harnai"

    mattermost_url: str = "http://localhost:8065"
    mattermost_team: str = "seaswarm"
    mattermost_channel: str = "sar-harnai"
    mattermost_admin_user: str = "admin"
    mattermost_admin_email: str = "admin@seaswarm.local"
    mattermost_admin_password: str = "SeaSwarm-Admin-2026!"
    mattermost_bot_token: str = ""
    ramesh_password: str = "SeaSwarm-Ramesh-2026!"
    sunita_password: str = "SeaSwarm-Sunita-2026!"
    token_store: str = "./.runtime/mm_tokens.json"

    followup_interval_seconds: int = 1800
    agent_name: str = "context"

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    discord_enabled: bool = False
    discord_bot_token: str = ""

    @property
    def bridge_enabled(self) -> bool:
        return self.switch_bridge.strip().lower() in {"1", "on", "true", "yes"}

    @property
    def persistence_enabled(self) -> bool:
        return self.persistence.strip().lower() not in {"0", "off", "false", "no"}


def get_settings() -> Settings:
    return Settings()
