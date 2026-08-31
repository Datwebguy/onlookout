#!/usr/bin/env python3
"""Reference scorer mirroring scorer/src/scoring.rs for local verification."""

from __future__ import annotations

import json
import math
from typing import Any


def clamp01(v: float) -> float:
    if math.isnan(v):
        return 0.0
    return max(0.0, min(1.0, v))


def relative_accuracy(gt: float, mr: float) -> float:
    denom = max(abs(gt), 1e-6)
    return clamp01(1.0 - abs(gt - mr) / denom)


def mae_score(pairs: list[tuple[float, float]]) -> float:
    if not pairs:
        return 0.0
    mae = sum(abs(g - m) for g, m in pairs) / len(pairs)
    return clamp01(1.0 / (1.0 + mae))


def rmse_score(pairs: list[tuple[float, float]]) -> float:
    if not pairs:
        return 0.0
    mse = sum((g - m) ** 2 for g, m in pairs) / len(pairs)
    return clamp01(1.0 / (1.0 + math.sqrt(mse)))


def severity_rank(flags: list[str]) -> int:
    rank = 0
    for f in flags:
        if f == "storm":
            rank = max(rank, 3)
        elif f == "heavy_precip":
            rank = max(rank, 2)
        elif f == "high_wind":
            rank = max(rank, 1)
    return rank


def evaluate(question: str, ground_truth: str, miner_response: str) -> float:
    _ = question
    if not miner_response.strip():
        return 0.0
    if ground_truth.strip() == miner_response.strip() and ground_truth.strip():
        return 1.0
    gt = json.loads(ground_truth)
    mr = json.loads(miner_response)
    g_rows = gt.get("forecast") or []
    m_rows = mr.get("forecast") or []
    n = min(len(g_rows), len(m_rows))
    if n == 0:
        return 0.0

    temp: list[tuple[float, float]] = []
    precip: list[tuple[float, float]] = []
    wind: list[tuple[float, float]] = []
    cond_hits = 0
    for i in range(n):
        if g_rows[i].get("temp_c") is not None and m_rows[i].get("temp_c") is not None:
            temp.append((float(g_rows[i]["temp_c"]), float(m_rows[i]["temp_c"])))
        if g_rows[i].get("precip_mm") is not None and m_rows[i].get("precip_mm") is not None:
            precip.append((float(g_rows[i]["precip_mm"]), float(m_rows[i]["precip_mm"])))
        if g_rows[i].get("wind_ms") is not None and m_rows[i].get("wind_ms") is not None:
            wind.append((float(g_rows[i]["wind_ms"]), float(m_rows[i]["wind_ms"])))
        if g_rows[i].get("conditions") is not None and g_rows[i].get("conditions") == m_rows[i].get("conditions"):
            cond_hits += 1

    temp_s = 0.5 * mae_score(temp) + 0.5 * rmse_score(temp)
    precip_s = 0.5 * mae_score(precip) + 0.5 * rmse_score(precip)
    wind_s = 0.5 * mae_score(wind) + 0.5 * rmse_score(wind)
    cond_s = cond_hits / n
    first_rel = 0.0
    if g_rows[0].get("temp_c") is not None and m_rows[0].get("temp_c") is not None:
        first_rel = relative_accuracy(float(g_rows[0]["temp_c"]), float(m_rows[0]["temp_c"]))
    point = clamp01(0.30 * temp_s + 0.25 * precip_s + 0.20 * wind_s + 0.15 * cond_s + 0.10 * first_rel)

    severity = clamp01(1.0 - abs(severity_rank(gt.get("risk_flags") or []) - severity_rank(mr.get("risk_flags") or [])) / 3.0)

    ga, ma = gt.get("as_of") or "", mr.get("as_of") or ""
    if ga and ma and ga == ma:
        fresh = 1.0
    elif len(ga) >= 10 and len(ma) >= 10 and ga[:10] == ma[:10]:
        fresh = 0.8
    elif ga and ma:
        fresh = 0.4
    else:
        fresh = 0.0

    ok = 0
    for row in m_rows:
        nums_ok = row.get("temp_c") is not None and row.get("precip_mm") is not None and row.get("wind_ms") is not None
        time_ok = bool(row.get("time"))
        cond_ok = bool(row.get("conditions")) and row.get("conditions") != "unknown"
        if nums_ok and time_ok and cond_ok:
            ok += 1
    structural = ok / len(m_rows) if m_rows else 0.0
    conf = mr.get("confidence")
    conf_ok = 1.0 if isinstance(conf, (int, float)) and 0.0 <= float(conf) <= 1.0 else 0.0
    consistency = clamp01(0.8 * structural + 0.2 * conf_ok)

    if isinstance(gt.get("confidence"), (int, float)) and isinstance(mr.get("confidence"), (int, float)):
        traffic = relative_accuracy(float(gt["confidence"]), float(mr["confidence"]))
    else:
        traffic = 0.0

    score = 0.45 * point + 0.15 * severity + 0.15 * fresh + 0.15 * consistency + 0.10 * traffic
    return round(clamp01(score), 6)


if __name__ == "__main__":
    sample = {
        "as_of": "2026-08-23T12:00:00Z",
        "confidence": 0.9,
        "risk_flags": ["none"],
        "forecast": [
            {
                "time": "2026-08-23T12:00:00Z",
                "temp_c": 20.0,
                "precip_mm": 0.0,
                "wind_ms": 3.0,
                "conditions": "clear",
            }
        ],
    }
    payload = json.dumps(sample)
    s = evaluate("Berlin forecast", payload, payload)
    assert s > 0.9, s
    print("ref_scorer_ok", s)
