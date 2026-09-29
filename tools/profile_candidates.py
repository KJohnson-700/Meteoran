"""Pull per-pool history for the ranked candidates and run T1 (vs-HODL) on each.

Point: a raw pnl_sol sort cannot tell a skilled LP from someone who farmed a token that
mooned. Several top candidates show pct_sol of 600-990%, which is exactly that profile.
vs_hodl splits it. This is the step that turns a candidate list into a shortlist.
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import report

N   = int(sys.argv[1]) if len(sys.argv) > 1 else 25
API = "https://dlmm.datapi.meteora.ag"

def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                             "Accept": "application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.4 * (a + 1))
    return {}

def pools(w):
    out = []
    for pg in range(1, 11):
        d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
        out += d.get("pools") or []
        if not d.get("hasNext"): break
    return out

cands = json.load(open("data/candidates.json"))[:N]
ws = [c["w"] for c in cands]
print(f"  pulling per-pool history for {len(ws)} candidates ...")
with ThreadPoolExecutor(max_workers=8) as ex:
    got = dict(zip(ws, ex.map(pools, ws)))
json.dump(got, open("data/candidate_pools.json", "w"))
print(f"  got {sum(len(v) for v in got.values()):,} pool rows\n")

res = {}
for c in cands:
    w = c["w"]
    if not got[w]: print(f"\n  === {w[:8]} === no pool data"); continue
    res[w] = report(f"{w[:8]}…  (rank pnl {c['pnl_sol']:+,.0f} SOL, pct_sol {100*c['pct_sol']:.0f}%)",
                    got[w])
json.dump(res, open("data/candidate_vs_hodl.json", "w"), indent=1)
