# OnLookout

Weather forecast miner and WASM scorer for Telegraph Protocol. Intent `WEATHER_FORECAST`.

- Live wrapper: https://onlookout.fly.dev
- Miner id: `910`
- Slug: `onlookout-weather`
- YAML: https://onlookout.fly.dev/miner.yaml
- On-chain miner registration: `196` (active)
- X: [@Datweb3guy](https://x.com/Datweb3guy)

## Track 1 — miner

Open-Meteo fusion wrapper serving live forecasts at `/v1/forecast`. Paid asks go through Telegraph x402 to miner `910`.

## Track 2 — WASM scorer (submit **1417**)

Hackathon form should use WASM registration **1417**.

| Field | Value |
| --- | --- |
| WASM id | `1417` |
| GitHub | https://github.com/Datwebguy/onlookout |
| Binary | https://onlookout.fly.dev/scorer.wasm |
| Eval | 15 / 15 fixture wins, self-match 1.0, margin 0.667 vs champion 0.990 |

1417 is a hybrid Jaccard + weather-fact `rank_answer` (city / sky / temp C-F / wind / precip / day-part) with a logistic stretch. Rejected on champion *separation* only — ABI, timeout, and ordering all passed.

Source: `scorer/` (`rank_answer` / `alloc` / `dealloc`, wazero 6×i32 → f32).

## Stack

- `wrapper/` FastAPI Open-Meteo fusion
- `miner/` Telegraph YAML
- `scorer/` WASM `rank_answer` module
- `agent/` paid Telegraph demand agent
