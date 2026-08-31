/**
 * Protocol path demand: paid ask through Telegraph engine to miner id 910.
 *
 *   npm install @x402/fetch @x402/evm viem
 *   $env:EVM_PRIVATE_KEY="0x..."   # set locally only
 *   $env:ONLOOKOUT_MINER_ID="910"
 *   node telegraph_paid_ask.mjs
 */
import { wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme, toClientEvmSigner } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const NODE = process.env.TELEGRAPH_NODE_URL || "https://devnode.telegraphprotocol.com";
const MINER_ID = process.env.ONLOOKOUT_MINER_ID || "910";
const key = process.env.EVM_PRIVATE_KEY;

if (!key || !key.startsWith("0x")) {
  console.error("Set EVM_PRIVATE_KEY in this terminal first (0x...).");
  process.exit(1);
}

const account = privateKeyToAccount(/** @type {`0x${string}`} */ (key));
const signer = toClientEvmSigner(account);

// Base Sepolia CAIP-2 id used by Telegraph 402 challenges: eip155:84532
const client = new x402Client().register(
  "eip155:84532",
  new ExactEvmScheme(signer)
);

const fetchWithPayment = wrapFetchWithPayment(fetch, client);

const body = {
  method: "GET",
  endpoint: "/forecast",
  payload: {
    latitude: Number(process.env.LAT || 52.52),
    longitude: Number(process.env.LON || 13.41),
    hours: Number(process.env.HOURS || 24),
    name: process.env.NAME || "Berlin",
  },
};

const url = `${NODE}/engine/v1/ask/${MINER_ID}`;
const res = await fetchWithPayment(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

const text = await res.text();
let parsed;
try {
  parsed = JSON.parse(text);
} catch {
  parsed = text;
}

console.log(
  JSON.stringify(
    {
      status: res.status,
      payer: account.address,
      miner_id: MINER_ID,
      body: parsed,
    },
    null,
    2
  )
);

if (!res.ok) process.exit(1);
