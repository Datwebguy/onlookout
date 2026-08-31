from __future__ import annotations

from typing import Any, Literal

Decision = Literal["GO", "DELAY", "REROUTE"]


def decide(payload: dict[str, Any], *, delay_wind: float, reroute_wind: float, delay_precip: float, reroute_precip: float) -> Decision:
    flags = [str(x) for x in (payload.get("risk_flags") or [])]
    if "storm" in flags:
        return "REROUTE"

    forecast = payload.get("forecast") or []
    max_wind = 0.0
    max_precip = 0.0
    for row in forecast:
        try:
            max_wind = max(max_wind, float(row.get("wind_ms") or 0.0))
            max_precip = max(max_precip, float(row.get("precip_mm") or 0.0))
        except (TypeError, ValueError):
            continue

    if "high_wind" in flags or max_wind >= reroute_wind:
        return "REROUTE"
    if "heavy_precip" in flags or max_precip >= reroute_precip:
        return "REROUTE"
    if max_wind >= delay_wind or max_precip >= delay_precip:
        return "DELAY"
    return "GO"
