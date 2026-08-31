from __future__ import annotations

from typing import Annotated

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from service import UpstreamError, build_forecast
from settings import get_settings

app = FastAPI(title="OnLookout Wrapper", version="1.0.0")


def _resolve_hours(hours: int | None, forecast_days: int | None) -> int:
    settings = get_settings()
    if hours is not None:
        value = hours
    elif forecast_days is not None:
        value = forecast_days * 24
    else:
        value = settings.default_forecast_hours
    return max(1, min(settings.max_forecast_hours, value))


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "OnLookout Weather Forecast Miner",
        "status": "online",
        "protocol": "Telegraph Protocol",
        "endpoints": {
            "health": "/healthz",
            "forecast": "/v1/forecast?latitude=52.52&longitude=13.41",
            "miner_yaml": "/miner.yaml",
        },
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "onlookout"}


@app.get("/miner.yaml", response_class=PlainTextResponse)
async def miner_yaml() -> str:
    path = Path(__file__).with_name("miner.yaml")
    if not path.exists():
        raise HTTPException(status_code=404, detail="miner yaml not found")
    return path.read_text(encoding="utf-8")


@app.get("/scorer.wasm")
async def scorer_wasm() -> Response:
    path = Path(__file__).with_name("scorer.wasm")
    if not path.exists():
        raise HTTPException(status_code=404, detail="scorer wasm not found")
    data = path.read_bytes()
    return Response(
        content=data,
        media_type="application/wasm",
        headers={
            "Content-Encoding": "identity",
            "Cache-Control": "no-transform, no-cache, must-revalidate",
            "Content-Length": str(len(data)),
        },
    )


from typing import Any
import httpx

from geocode import forward_geocode

def _parse_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


@app.get("/v1/forecast")
async def forecast(
    latitude: Any = Query(None),
    longitude: Any = Query(None),
    lat: Any = Query(None),
    lon: Any = Query(None),
    name: Annotated[str | None, Query()] = None,
    hours: Annotated[int | None, Query()] = None,
    forecast_days: Annotated[int | None, Query()] = None,
) -> JSONResponse:
    parsed_lat = _parse_float(latitude) if latitude is not None else _parse_float(lat)
    parsed_lon = _parse_float(longitude) if longitude is not None else _parse_float(lon)
    resolved_name = name

    if parsed_lat is None or parsed_lon is None:
        # Text prompt query (e.g. from Alexandria DIRECT REQUEST or unparsed string)
        text_query = str(latitude or lat or name or "")
        settings = get_settings()
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout_sec)) as client:
            geo = await forward_geocode(client, text_query)
            if geo:
                parsed_lat, parsed_lon, resolved_name = geo
            else:
                # Default fallback location if unparseable
                parsed_lat, parsed_lon, resolved_name = 52.52, 13.41, "Berlin"

    # Clamp coordinates to valid bounds
    clamped_lat = max(-90.0, min(90.0, parsed_lat))
    clamped_lon = max(-180.0, min(180.0, parsed_lon))

    settings = get_settings()
    try:
        payload = await build_forecast(
            settings,
            latitude=clamped_lat,
            longitude=clamped_lon,
            name=resolved_name,
            hours=_resolve_hours(hours, forecast_days),
        )
    except UpstreamError as exc:
        # No fabrication: fail cleanly when upstream cannot supply real data.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return JSONResponse(content=payload.model_dump())



def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
