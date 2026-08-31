#!/usr/bin/env python3
"""Generate real multi location WEATHER_FORECAST demand against live OnLookout."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from agent import run_once

# Diverse real coordinates for logistics style demand.
LOCATIONS: list[tuple[float, float, str]] = [
    (52.52, 13.41, "Berlin"),
    (40.71, -74.01, "NewYork"),
    (1.29, 103.85, "Singapore"),
    (-33.87, 151.21, "Sydney"),
    (35.68, 139.69, "Tokyo"),
    (51.51, -0.13, "London"),
    (25.20, 55.27, "Dubai"),
    (19.43, -99.13, "MexicoCity"),
    (28.61, 77.21, "NewDelhi"),
    (-23.55, -46.63, "SaoPaulo"),
]


async def run_batch(rounds: int, hours: int, pause_sec: float) -> dict:
    ok = 0
    fail = 0
    decisions: dict[str, int] = {}
    for r in range(rounds):
        for lat, lon, name in LOCATIONS:
            try:
                receipt = await run_once(lat, lon, name, hours)
                ok += 1
                d = str(receipt.get("decision") or "UNKNOWN")
                decisions[d] = decisions.get(d, 0) + 1
                print(json.dumps({"ok": True, "round": r + 1, "name": name, "decision": d}))
            except Exception as exc:
                fail += 1
                print(json.dumps({"ok": False, "round": r + 1, "name": name, "error": str(exc)}))
            if pause_sec > 0:
                await asyncio.sleep(pause_sec)
    summary = {
        "ok": ok,
        "fail": fail,
        "total": ok + fail,
        "decisions": decisions,
        "receipts_file": str(Path("agent_receipts.jsonl").resolve()),
    }
    print(json.dumps({"summary": summary}, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="OnLookout volume runner")
    parser.add_argument("--rounds", type=int, default=1, help="Passes over the location list")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--pause", type=float, default=0.5, help="Seconds between requests")
    args = parser.parse_args()
    asyncio.run(run_batch(args.rounds, args.hours, args.pause))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
