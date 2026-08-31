# OnLookout Scorer

WASM evaluation script for intent `WEATHER_FORECAST`.

Hackathon Track 2 submission: **WASM 1417**.

## Approach

Hybrid ranker, not MiniLM (24MB MiniLM times out on candidate eval):

1. Extract weather facts: city (with aliases), sky family, temperatures (C/F), wind, precip, day-part
2. Contradiction (wrong city, opposite sky, temp off by >8C, disjoint day) → ~0
3. Matching facts blend 60% Jaccard + 40% fact accuracy
4. Logistic stretch so paraphrases stay high and near-copies that swapped the city/sky stay low

Goal: Canonical scorer on `weather_forecast`. Champion to beat is MiniLM `#636` (margin ~0.99).

## Build
Do not use wasm-pack. Telegraph's wazero host expects a raw `wasm32-unknown-unknown`
module with C ABI exports, not a wasm-bindgen JS wrapper.

```bash
cargo test
rustup target add wasm32-unknown-unknown
cargo build --release --target wasm32-unknown-unknown
```
Binary: `target/wasm32-unknown-unknown/release/onlookout_scorer.wasm`

Required exports (official `telegraph-wasm-baseline` ABI):
- `rank_answer(i32,i32,i32,i32,i32,i32) -> f32`  question, ground_truth, miner_answer
- `alloc(i32) -> i32`
- `dealloc(i32, i32)`

Empty miner answer must return 0. Self-match must beat an unrelated cross-match.

## Register script
Diamond from resources.md (live):
`0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8`

Build note on Windows: MSVC Build Tools with link.exe are required for cargo and wasm-pack.

```bash
export DIAMOND="0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8"
export RPC="https://sepolia.base.org"
WASM_HASH="0x$(sha256sum pkg/onlookout_scorer_bg.wasm | awk '{print $1}')"
cast send "$DIAMOND" \
  "registerScript(string,bytes32)" \
  "ipfs://YOUR_CID" \
  "$WASM_HASH" \
  --rpc-url "$RPC" \
  --private-key "$PRIVATE_KEY"
```
