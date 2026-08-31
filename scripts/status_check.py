import json
import pathlib
import os
import urllib.request

T = os.environ["TEMP"]
UA = ("User-Agent", "OnLookout/1.0")


def load(path):
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text[:200]}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "OnLookout/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


m = load(os.path.join(T, "m174.json"))
if not m or "miner" not in m:
    try:
        m = fetch("https://devnode.telegraphprotocol.com/api/miners/174")
    except Exception as e:
        m = {"error": str(e)}

items = load(os.path.join(T, "wf.json"))
if not isinstance(items, list):
    try:
        items = fetch("https://devnode.telegraphprotocol.com/api/miners?intent=WEATHER_FORECAST")
    except Exception as e:
        items = []
        print("WF_FETCH_ERROR", e)

if isinstance(items, dict):
    items = items.get("miners") or items.get("data") or []

print("=== MINER REGISTRATION ===")
if isinstance(m, dict) and "miner" in m:
    mm = m["miner"]
    for k in [
        "registration_id",
        "slug",
        "activation_status",
        "supported_intents",
        "min_price_usdc",
        "registered_at",
        "updated_at",
        "rejection_reason",
    ]:
        print(f"{k}: {mm.get(k)}")
else:
    print(m)

print("\n=== WEATHER_FORECAST BOARD ===")
rows = []
for x in items:
    sc = x.get("scores") or []
    wf = [s for s in sc if s.get("intent_id") == "WEATHER_FORECAST"]
    top = wf[0] if wf else (sc[0] if sc else {})
    ours = x.get("slug") == "onlookout-weather" or str(x.get("id")) == "910"
    rows.append(
        {
            "rank": top.get("rank"),
            "score": top.get("score"),
            "epoch": x.get("last_scored_epoch") or top.get("epoch_id"),
            "id": x.get("id"),
            "slug": x.get("slug"),
            "scored": x.get("scored"),
            "ours": ours,
        }
    )

rows.sort(key=lambda r: (999 if r["rank"] is None else int(r["rank"]), r["slug"] or ""))
for r in rows:
    mark = "  <== OURS" if r["ours"] else ""
    print(
        f"rank={r['rank']} score={r['score']} epoch={r['epoch']} id={r['id']} {r['slug']} scored={r['scored']}{mark}"
    )

ours = next((r for r in rows if r["ours"]), None)
print("\n=== OURS ===")
print(json.dumps(ours, indent=2))
print("total_weather_miners", len(rows))

hz = load(os.path.join(T, "hz.json"))
fc = load(os.path.join(T, "fc.json"))
print("\n=== WRAPPER ===")
print("health", hz)
if isinstance(fc, dict) and "forecast" in fc:
    print("forecast_hours", len(fc.get("forecast") or []), "confidence", fc.get("confidence"), "flags", fc.get("risk_flags"))
else:
    print("forecast", fc)

paid = pathlib.Path(r"C:\Users\DELL\Downloads\OnLookout\agent\paid_receipts.jsonl")
direct = pathlib.Path(r"C:\Users\DELL\Downloads\OnLookout\agent\agent_receipts.jsonl")
for label, path in [("paid", paid), ("direct", direct)]:
    if not path.exists():
        print(f"{label}_lines 0")
        continue
    lines = path.read_text(encoding="utf-8").splitlines()
    ok = 0
    for line in lines:
        try:
            obj = json.loads(line)
            if obj.get("status") == 200 or obj.get("ok") is True:
                ok += 1
        except Exception:
            pass
    print(f"{label}_lines", len(lines), f"{label}_okish", ok)
