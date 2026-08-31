from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8080
    request_timeout_sec: float = 12.0

    open_meteo_base_url: str = "https://api.open-meteo.com"
    open_meteo_forecast_path: str = "/v1/forecast"

    # Optional secondary sources from resources.md. Used only when keys are present.
    openweathermap_base_url: str = "https://api.openweathermap.org"
    openweathermap_api_key: str | None = None
    weatherapi_base_url: str = "https://api.weatherapi.com"
    weatherapi_api_key: str | None = None

    default_forecast_hours: int = 48
    max_forecast_hours: int = 168

    # Risk thresholds used for risk_flags. Fully configurable.
    high_wind_ms: float = 15.0
    heavy_precip_mm: float = 5.0
    storm_weather_codes: str = "95,96,97,98,99"


@lru_cache
def get_settings() -> Settings:
    return Settings()
