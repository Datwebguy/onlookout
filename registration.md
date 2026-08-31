# Registration OnLookout

All values below come from resources.md architecture.md and memory.md plus the live YAML standard required for activation.

## Prerequisites
1. Join Discord at https://discord.com/invite/telegraphprotocol
2. Deploy the wrapper so it answers GET /v1/forecast with the product.md schema
3. Set ONLOOKOUT_BASE_URL to https://onlookout.fly.dev (Fly app name onlookout)
4. Hold Base Sepolia ETH for gas
5. Choose feeAddress as a non zero EVM wallet that will receive payouts
6. Install cast from Foundry

## Render and host YAML
```bash
export ONLOOKOUT_BASE_URL="https://YOUR_PUBLIC_WRAPPER_ORIGIN"
python scripts/render_miner_yaml.py
```
Host miner/onlookout-weather.yaml at a stable https or ipfs URL. Prefer IPFS via https://integrate.telegraphprotocol.com/

## Hash
yamlHash is SHA 256 of the exact hosted bytes. Not keccak.

```bash
sha256sum miner/onlookout-weather.yaml | awk '{print "0x"$1}'
```
Or after hosting:
```bash
curl -sL "$YAML_URL" | sha256sum | awk '{print "0x"$1}'
```

## On chain call
Diamond from resources.md (live registry):
`0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8`

minPriceUsdc from architecture.md and memory.md:
`10000` which is 0.01 USDC at 6 decimals

supportedIntents for primary intent weather_forecast in live canonical form:
`["WEATHER_FORECAST"]`

Casing is exact. `weather_forecast` reverts. `WEATHER_FORECAST` passes.

Verify before send:
```bash
export DIAMOND="0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8"
export RPC="https://sepolia.base.org"
cast call "$DIAMOND" "isCanonicalIntent(string)(bool)" "WEATHER_FORECAST" --rpc-url "$RPC"
cast call "$DIAMOND" "getCanonicalIntents()(string[])" --rpc-url "$RPC"
cast call "$DIAMOND" "minerCount()(uint256)" --rpc-url "$RPC"
```

Register:
```bash
export DIAMOND="0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8"
export RPC="https://sepolia.base.org"
export YAML_URL="https_or_ipfs_url_of_hosted_yaml"
export YAML_HASH="0xHASH_FROM_SHA256"
export FEE_ADDRESS="0xYOUR_FEE_ADDRESS"
export MINER_PRIVATE_KEY="0xYOUR_KEY"

cast send "$DIAMOND" \
  "registerMiner(string,bytes32,address,uint256,string[])" \
  "$YAML_URL" \
  "$YAML_HASH" \
  "$FEE_ADDRESS" \
  10000 \
  '["WEATHER_FORECAST"]' \
  --rpc-url "$RPC" \
  --private-key "$MINER_PRIVATE_KEY"
```

Recommended path with wallet UI and IPFS pin:
https://integrate.telegraphprotocol.com/

## Confirm activation
```bash
curl -s https://devnode.telegraphprotocol.com/api/miners | findstr onlookout-weather
```
Or by registrationId from the transaction receipt:
```bash
curl -s https://devnode.telegraphprotocol.com/api/miners/REGISTRATION_ID
```

Check explorer:
https://explorer.telegraphprotocol.com/

Check live queries:
https://alexandria.telegraphprotocol.com/

## Identity fields locked in YAML
- slug: onlookout-weather
- id: 910 (confirmed unused on live catalog at authoring time; recheck before register)
- protocol: generic
- kind: miner
- min_price_usdc: 0.01
