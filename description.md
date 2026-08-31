# OnLookout

OnLookout is a production weather forecast miner for the Telegraph Protocol. It serves the canonical intent `WEATHER_FORECAST` with an agent ready structured response, a matching WASM evaluation script, and a demand generating agent that turns live forecasts into GO, DELAY, or REROUTE decisions.

## What it does
A hosted wrapper pulls forecast data from Open Meteo as the primary source, optionally fuses a secondary source when credentials are present, and returns a fixed schema:

- location (lat, lon, name)
- as_of (UTC)
- forecast rows (time, temp_c, precip_mm, wind_ms, conditions)
- confidence (0 to 1)
- source (`open-meteo+fusion`)
- risk_flags (`none`, `high_wind`, `heavy_precip`, `storm`, ...)

Telegraph routes paid `WEATHER_FORECAST` requests to the registered miner. Validators score responses with the OnLookout WASM script. The agent creates real request volume and logs receipts.

## Why this build
Weather forecast is Tier A deterministic intent with clear agent value for logistics, travel, supply chain, risk, and IoT. Public competition exists (Zeus, OpenWeatherMap, WeatherAPI, OathCast), but there is room for cleaner structured output, calibrated confidence, risk flags, freshness, and a strong matching scorer.

## Stack in this repo
- `wrapper/` live service at https://onlookout.fly.dev
- `miner/onlookout-weather.yaml` Telegraph miner config (slug `onlookout-weather`, id `910`)
- `scorer/` WASM evaluation script for pointwise accuracy, severity ordering, freshness, consistency, and traffic agreement
- `agent/` demand agent with GO / DELAY / REROUTE decisions and receipt logging
- Docs: product schema, architecture, resources, registration, plan, memory

## Network facts used
- Live Diamond (Base Sepolia): `0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8`
- Floor price: 0.01 USDC (`10000` at 6 decimals)
- Intent registered as `WEATHER_FORECAST` (exact uppercase form required on chain)
- yamlHash: SHA 256 of hosted YAML bytes

## Current status
Wrapper is deployed and verified on Fly. YAML is rendered with the live base URL. Remaining work before full flywheel: register the miner on the live Diamond, build and register the WASM scorer, then run the demand agent against the live miner.
