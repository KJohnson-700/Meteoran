"""T2 stage 1 -- cache the per-pool rows for every T1-measured wallet.

skill_leaderboard.py stored only per-wallet summaries, so the time dimension was thrown
away. T2 needs pools keyed by lastClosedAt, so pull them once and keep ONLY the fields
vs_hodl() and the split need. Full rows for 2,840 wallets would be ~140MB; this is ~10x
smaller and lets us re-split on any cut date without touching the API again.

HARD LIMIT: days_back is capped at 365 -- 366+ returns HTTP 400 on every call. So the
whole visible history is a trailing year, and any cut date must sit inside it.

Resumable. Checkpoints every 200 wallets.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

OUT = "data/t2_pools.json"
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 16
API = "https://dlmm.datapi.meteora.ag"

KEEP = ("totalDepositSol", "totalWithdrawalSol", "totalFeeSol", "pnlSol",
        "totalDepositTokenX", "totalDepositTokenXSol",
        "totalWithdrawalTokenX", "totalWithdrawalTokenXSol",
        "totalDepositTokenY", "totalDepositTokenYSol",
        "totalWithdrawalTokenY", "totalWithdrawalTokenYSol")

def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                             "Accept": "application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}

def one(w):
    rows = []
    for pg in range(1, 11):
        d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
        rows += d.get("pools") or []
        if not d.get("hasNext"): break
    if not rows: return None
    slim = []
    for p in rows:
        if not p.get("lastClosedAt"): continue        # undated -> unusable for a time split
        o = {"p": p["poolAddress"], "t": int(p["lastClosedAt"])}
        for k in KEEP: o[k] = p.get(k)
        slim.append(o)
    return {"w": w, "pools": slim} if slim else None

lb = [r["w"] for r in json.load(open("data/skill_leaderboard.json"))]
# Wallets found by pool scan never went through skill_leaderboard, so they are absent
# from the cache and T2 would silently skip them rather than fail them. Pull them too.
for extra in ("data/scanned_wallets.json",):
    if os.path.exists(extra):
        lb += [x["w"] for x in json.load(open(extra))]
res = json.load(open(OUT)) if os.path.exists(OUT) else []
done = {r["w"] for r in res}
todo = [w for w in dict.fromkeys(lb) if w not in done]
print(f"  todo {len(todo):,}  cached {len(done):,}", flush=True)

t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(one, todo), 1):
        if r: res.append(r)
        if i % 200 == 0:
            json.dump(res, open(OUT, "w"))
            el = time.time() - t0
            print(f"  {i:,}/{len(todo):,}  {i/el:.1f} wal/s  "
                  f"eta {(len(todo)-i)/max(i/el,1e-9)/60:.0f} min", flush=True)
json.dump(res, open(OUT, "w"))
print(f"  DONE {len(res):,} wallets, {sum(len(r['pools']) for r in res):,} dated pools, "
      f"{time.time()-t0:.0f}s -> {OUT}")
