from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Live query surfaces from resources.md
    alexandria_base_url: str = "https://alexandria.telegraphprotocol.com"
    integrate_base_url: str = "https://integrate.telegraphprotocol.com"
    node_miners_url: str = "https://devnode.telegraphprotocol.com/api/miners"

    # Direct path to OnLookout wrapper when known
    onlookout_direct_url: str | None = None

    intent: str = "WEATHER_FORECAST"
    request_timeout_sec: float = 20.0
    log_path: str = "agent_receipts.jsonl"

    # Decision thresholds (m/s and mm) aligned with wrapper defaults; override via env.
    delay_wind_ms: float = 12.0
    reroute_wind_ms: float = 18.0
    delay_precip_mm: float = 3.0
    reroute_precip_mm: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
