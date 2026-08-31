from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from decide import decide
from settings import get_settings


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, ensure_ascii=True) + "\n")


async def resolve_onlookout_base(client: httpx.AsyncClient) -> str | None:
    settings = get_settings()
    if settings.onlookout_direct_url:
        return settings.onlookout_direct_url.rstrip("/")

    resp = await client.get(settings.node_miners_url)
    resp.raise_for_status()
    payload = resp.json()
    miners = payload if isinstance(payload, list) else payload.get("miners") or payload.get("data") or []
    for miner in miners:
        if miner.get("slug") == "onlookout-weather" and miner.get("activation_status") == "active":
            base = miner.get("base_url")
            if base:
                return str(base).rstrip("/")
    return None


async def query_forecast(
    client: httpx.AsyncClient,
    base: str,
    *,
    latitude: float,
    longitude: float,
    name: str | None,
    hours: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "hours": hours,
    }
    if name:
        params["name"] = name
    resp = await client.get(f"{base}/v1/forecast", params=params)
    resp.raise_for_status()
    return resp.json()


async def run_once(latitude: float, longitude: float, name: str | None, hours: int) -> dict[str, Any]:
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as client:
        base = await resolve_onlookout_base(client)
        if not base:
            raise RuntimeError("onlookout-weather is not resolvable yet; set ONLOOKOUT_DIRECT_URL or wait for activation")

        body = await query_forecast(
            client,
            base,
            latitude=latitude,
            longitude=longitude,
            name=name,
            hours=hours,
        )

    decision = decide(
        body,
        delay_wind=settings.delay_wind_ms,
        reroute_wind=settings.reroute_wind_ms,
        delay_precip=settings.delay_precip_mm,
        reroute_precip=settings.reroute_precip_mm,
    )

    receipt = {
        "ts": _now(),
        "intent": settings.intent,
        "path": "direct_wrapper",
        "query": {"latitude": latitude, "longitude": longitude, "name": name, "hours": hours},
        "decision": decision,
        "confidence": body.get("confidence"),
        "risk_flags": body.get("risk_flags"),
        "as_of": body.get("as_of"),
        "source": body.get("source"),
        "forecast_hours": len(body.get("forecast") or []),
        "surfaces": {
            "alexandria": settings.alexandria_base_url,
            "integrate": settings.integrate_base_url,
            "miners": settings.node_miners_url,
        },
    }
    _append_receipt(Path(settings.log_path), receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="OnLookout demand agent")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    import asyncio

    try:
        receipt = asyncio.run(run_once(args.lat, args.lon, args.name, args.hours))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
