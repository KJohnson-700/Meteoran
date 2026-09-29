"""Is more accumulation worth it? Measure the YIELD of newly-discovered wallets.

Rule 1 said union repeated snapshots because a point-in-time getProgramAccounts scan
over-samples wallets that hold continuously. True, but discovery decays hard (112/hr in
hour 6, ~28/hr by hour 48), so the 100k bar is 20 days away and a saturating fit never
reaches it. The decision is not "is the bar reachable" but "does a marginal wallet carry
a marginal candidate". That is measurable: screen the wallets found SINCE the seed
snapshot and compare their pass rate against the seed population's.
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 12

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}

def total(w):
    d = get(f"{API}/portfolio/total?user={w}")
    if not d: return None
    try:
        return {"w": w, "pnl_sol": float(d.get("totalPnlSol") or 0),
                "pnl_usd": float(d.get("totalPnlUsd") or 0),
                "closed": int(d.get("totalClosedPositions") or 0)}
    except (TypeError, ValueError):
        return None

def ok(r):
    """Rule 2 corruption filters."""
    if r["closed"] <= 0: return False
    pct = r["pnl_sol"] / max(abs(r["pnl_sol"]), 1)   # placeholder, see below
    return (abs(r["pnl_sol"]) < 50_000 and abs(r["pnl_usd"]) < 5_000_000
            and r["pnl_sol"] * r["pnl_usd"] >= 0)

u = json.load(open("data/dlmm_universe.json"))
t0 = u["first_ts"]
new = [w for w, v in u["wallets"].items() if v["first"] > t0 + 60]
print(f"  {len(new):,} wallets discovered after the seed snapshot", flush=True)

t = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    res = [r for r in ex.map(total, new) if r]
json.dump(res, open("data/discovery_yield.json", "w"), indent=1)
print(f"  {len(res):,} returned P&L in {time.time()-t:.0f}s\n")

seed = [r for r in json.load(open("data/dlmm_pnl.json")) if r.get("closed") is not None]
def rates(lab, rows, n_total):
    clean = [r for r in rows if ok(r)]
    c20 = [r for r in clean if 20 <= r["closed"] <= 2000]
    prof = [r for r in c20 if r["pnl_sol"] > 0]
    print(f"  {lab:<28}{n_total:>9,}{len(clean):>10,}{len(c20):>11,}"
          f"{100*len(c20)/max(n_total,1):>9.2f}%{len(prof):>9,}"
          f"{100*len(prof)/max(len(c20),1):>9.0f}%")

print(f"  {'population':<28}{'wallets':>9}{'clean':>10}{'20-2000':>11}"
      f"{'yield':>9}{'profit':>9}{'of those':>9}")
rates("seed snapshot (baseline)", seed, len(seed))
rates("discovered in last 48h", res, len(new))

c20_new = [r for r in res if ok(r) and 20 <= r["closed"] <= 2000]
print(f"\n  A candidate is a wallet worth running T1 on (clean, 20-2000 closes).")
if c20_new:
    print(f"  New wallets yield {len(c20_new)} candidates from {len(new):,} discovered "
          f"over 48h = {len(c20_new)/48:.2f} candidates/hour.")
    print(f"  20 more days at that rate: ~{len(c20_new)/48*24*20:.0f} extra candidates, "
          f"against {len(seed):,} already screened.")
else:
    print(f"  New wallets yielded ZERO candidates in 48h of accumulation.")
