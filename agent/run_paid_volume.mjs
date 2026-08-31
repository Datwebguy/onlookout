/**
 * Loop paid Telegraph asks to miner 910 for protocol volume.
 * Reuses EVM_PRIVATE_KEY already set in the terminal.
 *
 *   $env:ONLOOKOUT_MINER_ID="910"
 *   $env:PAID_ROUNDS="10"
 *   node run_paid_volume.mjs
 */
import { wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme, toClientEvmSigner } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { appendFileSync } from "node:fs";

const NODE = process.env.TELEGRAPH_NODE_URL || "https://devnode.telegraphprotocol.com";
const MINER_ID = process.env.ONLOOKOUT_MINER_ID || "910";
const ROUNDS = Number(process.env.PAID_ROUNDS || 10);
const PAUSE_MS = Number(process.env.PAID_PAUSE_MS || 1500);
const LOG = process.env.PAID_LOG || "paid_receipts.jsonl";
const key = process.env.EVM_PRIVATE_KEY;

if (!key?.startsWith("0x")) {
  console.error("Set EVM_PRIVATE_KEY in this terminal first.");
  process.exit(1);
}

const LOCATIONS = [
  [52.52, 13.41, "Berlin"],
  [40.71, -74.01, "NewYork"],
  [1.29, 103.85, "Singapore"],
  [-33.87, 151.21, "Sydney"],
  [35.68, 139.69, "Tokyo"],
  [51.51, -0.13, "London"],
  [25.2, 55.27, "Dubai"],
  [19.43, -99.13, "MexicoCity"],
  [28.61, 77.21, "NewDelhi"],
  [-23.55, -46.63, "SaoPaulo"],
];

const account = privateKeyToAccount(/** @type {`0x${string}`} */ (key));
const signer = toClientEvmSigner(account);
const client = new x402Client().register("eip155:84532", new ExactEvmScheme(signer));
const fetchWithPayment = wrapFetchWithPayment(fetch, client);

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

let ok = 0;
let fail = 0;

for (let round = 1; round <= ROUNDS; round++) {
  for (const [lat, lon, name] of LOCATIONS) {
    const body = {
      method: "GET",
      endpoint: "/forecast",
      payload: {
        latitude: lat,
        longitude: lon,
        hours: Number(process.env.HOURS || 24),
        name,
      },
    };
    try {
      const res = await fetchWithPayment(`${NODE}/engine/v1/ask/${MINER_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const parsed = await res.json().catch(() => ({}));
      const row = {
        ts: new Date().toISOString(),
        status: res.status,
        round,
        name,
        miner_id: parsed.miner_id || MINER_ID,
        cost_usd: parsed.cost_usd,
        signal_hash: parsed.signal_hash,
        confidence: parsed.result?.confidence,
        risk_flags: parsed.result?.risk_flags,
      };
      appendFileSync(LOG, JSON.stringify(row) + "\n");
      if (res.ok) {
        ok += 1;
        console.log(JSON.stringify({ ok: true, ...row }));
      } else {
        fail += 1;
        console.log(JSON.stringify({ ok: false, ...row, body: parsed }));
      }
    } catch (err) {
      fail += 1;
      const row = { ts: new Date().toISOString(), round, name, error: String(err) };
      appendFileSync(LOG, JSON.stringify(row) + "\n");
      console.log(JSON.stringify({ ok: false, ...row }));
    }
    await sleep(PAUSE_MS);
  }
}

console.log(JSON.stringify({ summary: { ok, fail, total: ok + fail, log: LOG } }, null, 2));
