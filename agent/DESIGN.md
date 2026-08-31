# OnLookout Demand Agent

## Purpose
Generate real WEATHER_FORECAST demand against live OnLookout miners. Produce operational decisions GO DELAY REROUTE. Persist receipts and request volume.

## Inputs
- latitude longitude from the caller at runtime
- optional name and hours
- ONLOOKOUT_DIRECT_URL when wrapper origin is known
- otherwise resolve slug onlookout-weather from https://devnode.telegraphprotocol.com/api/miners

## Query paths
1. Direct wrapper GET /v1/forecast
2. Catalog discovery via miners API
3. Operator also monitors https://alexandria.telegraphprotocol.com/ and https://integrate.telegraphprotocol.com/

## Decision rules
- storm flag => REROUTE
- wind or precip above reroute thresholds => REROUTE
- wind or precip above delay thresholds => DELAY
- else GO

Thresholds are env driven. Defaults align with wrapper risk thresholds in settings.

## Outputs
JSON receipt appended to agent_receipts.jsonl with:
- ts intent path query decision confidence risk_flags as_of source forecast_hours surfaces

## Run single query
```bash
cd agent
pip install -r requirements.txt
set ONLOOKOUT_DIRECT_URL=https://onlookout.fly.dev
python agent.py --lat 52.52 --lon 13.41 --name Berlin --hours 24
```

## Volume runner direct path
Hits the live wrapper many times across cities. Receipts go to agent_receipts.jsonl.

```bash
cd agent
python run_volume.py --rounds 10 --hours 24 --pause 0.5
```

## Protocol path paid Telegraph asks
Counts as on protocol demand via x402. Needs Base Sepolia USDC and EVM_PRIVATE_KEY.

```bash
cd agent
npm install @x402/fetch @x402/evm
set EVM_PRIVATE_KEY=0xYOUR_KEY
node telegraph_paid_ask.mjs
```

Target: POST https://devnode.telegraphprotocol.com/engine/v1/ask/910
Body method GET endpoint /forecast payload lat lon hours.

## Volume
Count lines in agent_receipts.jsonl for direct path. For protocol path keep payment receipts and signal_hash from responses. Do not invent traffic.
