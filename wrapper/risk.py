from __future__ import annotations

from schema import ForecastRow
from settings import Settings


def build_risk_flags(rows: list[ForecastRow], settings: Settings) -> list[str]:
    stormish = {
        "thunderstorm",
        "thunderstorm_slight_hail",
        "thunderstorm_heavy",
        "thunderstorm_heavy_hail",
    }
    # Also accept raw wmo_NN labels if a code falls outside the named map.
    storm_codes = {int(x.strip()) for x in settings.storm_weather_codes.split(",") if x.strip()}
    for code in storm_codes:
        stormish.add(f"wmo_{code}")

    flags: list[str] = []

    if any(r.wind_ms >= settings.high_wind_ms for r in rows):
        flags.append("high_wind")
    if any(r.precip_mm >= settings.heavy_precip_mm for r in rows):
        flags.append("heavy_precip")
    if any(r.conditions in stormish for r in rows):
        flags.append("storm")

    if not flags:
        return ["none"]
    return flags
