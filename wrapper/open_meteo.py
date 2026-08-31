from __future__ import annotations

from typing import Any

import httpx

from conditions import conditions_from_wmo
from schema import ForecastRow
from settings import Settings


class UpstreamError(RuntimeError):
    pass


async def fetch_open_meteo(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    latitude: float,
    longitude: float,
    hours: int,
) -> tuple[list[ForecastRow], dict[str, Any]]:
    forecast_days = max(1, min(16, (hours + 23) // 24))
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,weather_code",
        "wind_speed_unit": "ms",
        "timezone": "UTC",
        "forecast_days": forecast_days,
    }
    url = settings.open_meteo_base_url.rstrip("/") + settings.open_meteo_forecast_path
    try:
        resp = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise UpstreamError(f"open_meteo transport failure: {exc}") from exc

    if resp.status_code != 200:
        raise UpstreamError(f"open_meteo http {resp.status_code}")

    payload = resp.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    precips = hourly.get("precipitation") or []
    winds = hourly.get("wind_speed_10m") or []
    codes = hourly.get("weather_code") or []

    n = min(len(times), len(temps), len(precips), len(winds), len(codes), hours)
    if n == 0:
        raise UpstreamError("open_meteo returned empty hourly series")

    rows: list[ForecastRow] = []
    for i in range(n):
        if temps[i] is None or precips[i] is None or winds[i] is None:
            continue
        code = codes[i] if i < len(codes) else None
        rows.append(
            ForecastRow(
                time=f"{times[i]}Z" if "Z" not in str(times[i]) and "+" not in str(times[i]) else str(times[i]),
                temp_c=float(temps[i]),
                precip_mm=float(precips[i]),
                wind_ms=float(winds[i]),
                conditions=conditions_from_wmo(None if code is None else int(code)),
            )
        )

    if not rows:
        raise UpstreamError("open_meteo produced no usable hourly rows")

    meta = {
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "elevation": payload.get("elevation"),
        "generationtime_ms": payload.get("generationtime_ms"),
    }
    return rows, meta
