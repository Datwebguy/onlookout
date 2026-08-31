from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from schema import ForecastRow
from settings import Settings


async def fetch_openweathermap_hourly(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    latitude: float,
    longitude: float,
    hours: int,
) -> list[ForecastRow] | None:
    key = settings.openweathermap_api_key
    if not key:
        return None

    url = settings.openweathermap_base_url.rstrip("/") + "/data/2.5/forecast"
    params = {"lat": latitude, "lon": longitude, "appid": key, "units": "metric"}
    try:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except httpx.HTTPError:
        return None

    rows: list[ForecastRow] = []
    for item in data.get("list") or []:
        if len(rows) >= hours:
            break
        main = item.get("main") or {}
        wind = item.get("wind") or {}
        rain = item.get("rain") or {}
        weather = (item.get("weather") or [{}])[0]
        ts = item.get("dt")
        if ts is None or main.get("temp") is None:
            continue
        time = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        precip = float(rain.get("3h") or 0.0) / 3.0
        rows.append(
            ForecastRow(
                time=time,
                temp_c=float(main["temp"]),
                precip_mm=precip,
                wind_ms=float(wind.get("speed") or 0.0),
                conditions=str(weather.get("description") or "unknown").replace(" ", "_"),
            )
        )
    return rows or None


async def fetch_weatherapi_hourly(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    latitude: float,
    longitude: float,
    hours: int,
) -> list[ForecastRow] | None:
    key = settings.weatherapi_api_key
    if not key:
        return None

    days = max(1, min(3, (hours + 23) // 24))
    url = settings.weatherapi_base_url.rstrip("/") + "/v1/forecast.json"
    params = {"key": key, "q": f"{latitude},{longitude}", "days": days, "aqi": "no", "alerts": "no"}
    try:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except httpx.HTTPError:
        return None

    rows: list[ForecastRow] = []
    forecast_days = ((data.get("forecast") or {}).get("forecastday") or [])
    for day in forecast_days:
        for hour in day.get("hour") or []:
            if len(rows) >= hours:
                break
            if hour.get("temp_c") is None:
                continue
            time_epoch = hour.get("time_epoch")
            if time_epoch is None:
                continue
            time = datetime.fromtimestamp(int(time_epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            condition = ((hour.get("condition") or {}).get("text") or "unknown").replace(" ", "_").lower()
            # weatherapi wind is kph by default
            wind_kph = float(hour.get("wind_kph") or 0.0)
            rows.append(
                ForecastRow(
                    time=time,
                    temp_c=float(hour["temp_c"]),
                    precip_mm=float(hour.get("precip_mm") or 0.0),
                    wind_ms=wind_kph / 3.6,
                    conditions=condition,
                )
            )
    return rows or None


def fuse_rows(primary: list[ForecastRow], secondary: list[ForecastRow]) -> list[ForecastRow]:
    by_hour: dict[str, ForecastRow] = {}
    for row in secondary:
        key = row.time[:13]  # YYYY-MM-DDTHH
        by_hour[key] = row

    fused: list[ForecastRow] = []
    for row in primary:
        key = row.time[:13]
        other = by_hour.get(key)
        if other is None:
            fused.append(row)
            continue
        fused.append(
            ForecastRow(
                time=row.time,
                temp_c=round((row.temp_c + other.temp_c) / 2.0, 3),
                precip_mm=round((row.precip_mm + other.precip_mm) / 2.0, 3),
                wind_ms=round((row.wind_ms + other.wind_ms) / 2.0, 3),
                conditions=row.conditions,
            )
        )
    return fused


async def maybe_fuse(
    client: httpx.AsyncClient,
    settings: Settings,
    primary: list[ForecastRow],
    *,
    latitude: float,
    longitude: float,
    hours: int,
) -> tuple[list[ForecastRow], bool, dict[str, Any]]:
    secondary = await fetch_openweathermap_hourly(
        client, settings, latitude=latitude, longitude=longitude, hours=hours
    )
    source_name = "openweathermap"
    if secondary is None:
        secondary = await fetch_weatherapi_hourly(
            client, settings, latitude=latitude, longitude=longitude, hours=hours
        )
        source_name = "weatherapi"

    if not secondary:
        return primary, False, {}

    return fuse_rows(primary, secondary), True, {"secondary": source_name}
