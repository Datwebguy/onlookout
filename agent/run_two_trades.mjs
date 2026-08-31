/**
 * Two paid Telegraph asks. Loads EVM_PRIVATE_KEY from agent/.env.
 * Does not print the key.
 */
import { wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme, toClientEvmSigner } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { appendFileSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
for (const line of readFileSync(join(here, ".env"), "utf8").split(/\r?\n/)) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
  const eq = trimmed.indexOf("=");
  const k = trimmed.slice(0, eq);
  let v = trimmed.slice(eq + 1);
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
    v = v.slice(1, -1);
  }
  if (!process.env[k]) process.env[k] = v;
}

const NODE = process.env.TELEGRAPH_NODE_URL || "https://devnode.telegraphprotocol.com";
const MINER_ID = process.env.ONLOOKOUT_MINER_ID || "910";
const LOG = process.env.PAID_LOG || join(here, "paid_receipts.jsonl");
const key = process.env.EVM_PRIVATE_KEY;

if (!key?.startsWith("0x") || key.length < 66) {
  console.error("EVM_PRIVATE_KEY missing or malformed in agent/.env");
  process.exit(1);
}

const TRADES = [
  { latitude: 52.52, longitude: 13.41, name: "Berlin", hours: 24 },
  { latitude: 40.71, longitude: -74.01, name: "NewYork", hours: 24 },
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

for (const payload of TRADES) {
  const body = { method: "GET", endpoint: "/forecast", payload };
  try {
    const res = await fetchWithPayment(`${NODE}/engine/v1/ask/${MINER_ID}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const parsed = await res.json().catch(() => ({}));
    const result = parsed.result || {};
    const row = {
      ts: new Date().toISOString(),
      status: res.status,
      name: payload.name,
      miner_id: parsed.miner_id || MINER_ID,
      miner_name: parsed.miner_name,
      cost_usd: parsed.cost_usd,
      signal_hash: parsed.signal_hash,
      confidence: result.confidence,
      risk_flags: result.risk_flags,
      answer: result.answer,
      summary: result.summary,
      as_of: result.as_of,
    };
    appendFileSync(LOG, JSON.stringify(row) + "\n");
    if (res.ok) {
      ok += 1;
      console.log(JSON.stringify({ ok: true, ...row }));
    } else {
      fail += 1;
      console.log(JSON.stringify({ ok: false, ...row, error: parsed.error || parsed }));
    }
  } catch (err) {
    fail += 1;
    const row = { ts: new Date().toISOString(), name: payload.name, error: String(err) };
    appendFileSync(LOG, JSON.stringify(row) + "\n");
    console.log(JSON.stringify({ ok: false, ...row }));
  }
  await sleep(1500);
}

console.log(JSON.stringify({ summary: { ok, fail, payer: account.address, miner_id: MINER_ID } }));
if (fail) process.exit(1);
