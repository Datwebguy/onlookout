from __future__ import annotations

import re
import httpx


async def forward_geocode(
    client: httpx.AsyncClient,
    query: str,
) -> tuple[float, float, str] | None:
    """Extract location name from raw text query and geocode to (lat, lon, name)."""
    if not query or not query.strip():
        return None

    import urllib.parse

    cleaned = re.sub(r"[^\w\s-]", " ", query).strip()
    words = [
        w
        for w in cleaned.split()
        if len(w) > 1
        and w.lower()
        not in {
            "what", "is", "the", "weather", "forecast", "for", "in", "today", "tomorrow",
            "hourly", "daily", "24-hour", "7-day", "can", "you", "provide", "starting", "from", "utc",
            "are", "there", "any", "storm", "alerts", "or", "high", "wind", "risks", "precipitation",
            "and", "temperature", "humidity", "check", "outlook", "give", "me", "conditions", "now", "please"
        }
    ]

    candidates = []
    if words:
        candidates.append(" ".join(words))
        if len(words) > 1:
            candidates.append(words[-1])
            candidates.append(" ".join(words[-2:]))
    else:
        candidates.append(cleaned)

    url = "https://geocoding-api.open-meteo.com/v1/search"
    for candidate in candidates:
        if not candidate.strip():
            continue
        params = {"name": candidate.strip(), "count": 1, "language": "en", "format": "json"}
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results") or []
                if results:
                    res = results[0]
                    lat = float(res.get("latitude", 0.0))
                    lon = float(res.get("longitude", 0.0))
                    name = str(res.get("name") or candidate.strip())
                    return lat, lon, name
        except httpx.HTTPError:
            pass
    return None


async def reverse_place_name(
    client: httpx.AsyncClient,
    *,
    latitude: float,
    longitude: float,
) -> str | None:
    """Best effort place label via Nominatim reverse with a clear UA."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "zoom": 10,
    }
    headers = {"User-Agent": "OnLookoutWeatherMiner/1.0 (telegraph miner)"}
    try:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except httpx.HTTPError:
        return None

    address = data.get("address") or {}
    for key in ("city", "town", "village", "municipality", "county", "state"):
        value = address.get(key)
        if value:
            country = address.get("country_code")
            if country:
                return f"{value}"
            return str(value)
    display = data.get("name") or data.get("display_name")
    if display:
        return str(display).split(",")[0].strip()
    return None

