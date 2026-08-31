from __future__ import annotations

from datetime import datetime, timezone

import httpx

from confidence import calibrate_confidence
from geocode import reverse_place_name
from open_meteo import UpstreamError, fetch_open_meteo
from risk import build_risk_flags
from schema import Location, MinerResponse
from secondary import maybe_fuse
from settings import Settings
from summarize import build_answer, build_canonical, build_days, build_summary


async def build_forecast(
    settings: Settings,
    *,
    latitude: float,
    longitude: float,
    name: str | None,
    hours: int,
) -> MinerResponse:
    timeout = httpx.Timeout(settings.request_timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as client:
        primary_rows, meta = await fetch_open_meteo(
            client,
            settings,
            latitude=latitude,
            longitude=longitude,
            hours=hours,
        )
        rows, secondary_used, _fuse_meta = await maybe_fuse(
            client,
            settings,
            primary_rows,
            latitude=latitude,
            longitude=longitude,
            hours=hours,
        )

        resolved_lat = float(meta.get("latitude", latitude))
        resolved_lon = float(meta.get("longitude", longitude))
        place_resolved = False
        if name and name.strip():
            label = name.strip()
            place_resolved = True
        else:
            resolved = await reverse_place_name(
                client, latitude=resolved_lat, longitude=resolved_lon
            )
            if resolved:
                label = resolved
                place_resolved = True
            else:
                label = f"{resolved_lat:.4f},{resolved_lon:.4f}"

    as_of_dt = datetime.now(timezone.utc)
    as_of = as_of_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    flags = build_risk_flags(rows, settings)
    conf = calibrate_confidence(
        rows,
        requested_hours=hours,
        secondary_used=secondary_used,
        as_of=as_of_dt,
        place_resolved=place_resolved,
    )
    days = build_days(rows)
    summary = build_summary(label, days, flags)
    first = rows[0] if rows else None
    answer = build_answer(summary, first)
    canonical = build_canonical(
        lat=resolved_lat,
        lon=resolved_lon,
        as_of=as_of,
        first=first,
        flags=flags,
        confidence=conf,
    )

    return MinerResponse(
        location=Location(lat=resolved_lat, lon=resolved_lon, name=label),
        as_of=as_of,
        forecast=rows,
        days=days,
        confidence=conf,
        source="open-meteo+fusion",
        risk_flags=flags,
        summary=summary,
        answer=answer,
        canonical=canonical,
    )


__all__ = ["build_forecast", "UpstreamError"]
