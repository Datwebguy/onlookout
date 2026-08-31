from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskFlag = Literal["none", "high_wind", "heavy_precip", "storm"]


class Location(BaseModel):
    lat: float
    lon: float
    name: str


class ForecastRow(BaseModel):
    time: str
    temp_c: float
    precip_mm: float
    wind_ms: float
    conditions: str


class DaySummary(BaseModel):
    date: str
    label: str
    high_c: float
    low_c: float
    precip_mm: float
    condition: str


class MinerResponse(BaseModel):
    location: Location
    as_of: str
    forecast: list[ForecastRow]
    days: list[DaySummary]
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["open-meteo+fusion"]
    risk_flags: list[str]
    summary: str
    answer: str
    canonical: str
