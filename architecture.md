# Architecture – OnLookout

## Components
1. **Wrapper Service** (your hosted endpoint)
   - Calls Open-Meteo (primary) ± secondary source
   - Normalizes to canonical schema
   - Adds confidence, as_of, risk_flags
   - Handles errors gracefully (no fabrication)

2. **YAML Miner Config**
   - protocol: generic
   - supported_intents: ["WEATHER_FORECAST"]
   - Clean param_map for lat/lon etc.
   - min_price_usdc: 0.01


3. **WASM Evaluation Script**
   - Scores: point-wise accuracy (MAE/RMSE), severity ordering, freshness, consistency, real-traffic agreement
   - Aim to become (or challenge) the live Canonical scorer for weather_forecast

4. **Track 3 Agent**
   - Queries OnLookout via Telegraph / Alexandria / direct
   - Produces GO/DELAY/REROUTE decisions
   - Logs receipts and request volume

## Data Flow
Agent → Telegraph Intent (weather_forecast) → Probabilistic routing to top OnLookout / competitors → OnLookout wrapper → Open-Meteo → Structured response → x402 payment → on-chain settlement → Validators run WASM scoring → Ranking update.

## Registration Flow
1. Write & host YAML
2. Compute SHA-256 hash
3. Call registerMiner on Diamond with yamlUrl, yamlHash, feeAddress, minPriceUsdc=10000, supportedIntents
4. Monitor activation at next epoch
