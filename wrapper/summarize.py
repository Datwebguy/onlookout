from __future__ import annotations

from collections import defaultdict

from schema import DaySummary, ForecastRow


def build_days(rows: list[ForecastRow]) -> list[DaySummary]:
    buckets: dict[str, list[ForecastRow]] = defaultdict(list)
    for row in rows:
        day = row.time[:10]
        buckets[day].append(row)

    days: list[DaySummary] = []
    for i, day in enumerate(sorted(buckets.keys())):
        group = buckets[day]
        temps = [r.temp_c for r in group]
        precip = sum(r.precip_mm for r in group)
        # Dominant condition by frequency.
        counts: dict[str, int] = defaultdict(int)
        for r in group:
            counts[r.conditions] += 1
        condition = max(counts.items(), key=lambda kv: kv[1])[0]
        label = "today" if i == 0 else ("tomorrow" if i == 1 else day)
        days.append(
            DaySummary(
                date=day,
                label=label,
                high_c=round(max(temps), 1),
                low_c=round(min(temps), 1),
                precip_mm=round(precip, 2),
                condition=condition,
            )
        )
    return days


def build_summary(location_name: str, days: list[DaySummary], flags: list[str]) -> str:
    if not days:
        return f"{location_name} forecast unavailable."
    today = days[0]
    parts = [
        f"{location_name} forecast: {today.label} high {today.high_c:.0f}C low {today.low_c:.0f}C {today.condition.replace('_', ' ')}"
    ]
    if len(days) > 1:
        nxt = days[1]
        parts.append(
            f"{nxt.label} high {nxt.high_c:.0f}C low {nxt.low_c:.0f}C {nxt.condition.replace('_', ' ')}"
        )
    risk = [f for f in flags if f != "none"]
    if risk:
        parts.append("risk " + ", ".join(r.replace("_", " ") for r in risk))
    return "; ".join(parts) + "."


def build_answer(summary: str, first: ForecastRow | None) -> str:
    if first is None:
        return summary
    return (
        f"{summary} Nearest hour {first.time}: {first.temp_c:.1f}C, "
        f"{first.precip_mm:.1f}mm, {first.wind_ms:.1f}m/s, {first.conditions.replace('_', ' ')}."
    )


def build_canonical(
    *,
    lat: float,
    lon: float,
    as_of: str,
    first: ForecastRow | None,
    flags: list[str],
    confidence: float,
) -> str:
    flag = flags[0] if flags else "none"
    if first is None:
        return f"WEATHER_FORECAST|{lat:.4f},{lon:.4f}|{as_of}|none|{confidence:.3f}"
    return (
        f"WEATHER_FORECAST|{lat:.4f},{lon:.4f}|{as_of}|"
        f"{first.temp_c:.1f}C|{first.precip_mm:.1f}mm|{first.wind_ms:.1f}ms|"
        f"{first.conditions}|{flag}|c{confidence:.3f}"
    )
