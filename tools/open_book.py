"""THE CENSORING GATE. Realised P&L is conditioned on the LP choosing to exit.

A wallet that books its winners and leaves its losers open, out of range and rotting,
reads as skilled on every realised metric we have -- T1, T2, beat-rate, all of it. The
open book is where that shows up, and nothing upstream looked at it.

`/portfolio/open` is the right source: one call per page, it covers pools whose last
close is OLDER than the 365d /portfolio window, and the per-position cache does not.
Measured on the T2 shortlist it found the top pick was carrying 81 open positions, 77 of
them out of range, median age 75 days, each down 90-97%, nothing withdrawn -- turning a
+5.7% realised record into -1.5% all-in.

    all-in = (realised pnl + unrealised pnl) / (closed capital + open capital)

Usage: python3 tools/open_book.py [wallets.json|addr,addr,...] [OUT.json]
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/t2_survivors.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/open_book.json"
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 12

# The closed side is already on disk for every measured wallet -- data/t2_pools.json
# carries dated per-pool rows with totalDepositSol and pnlSol. Re-pulling /portfolio for
# 2,849 wallets would be ~10 calls each for numbers we have, so read the cache and spend
# API calls only on /portfolio/open.
CLOSED = {}
if os.path.exists("data/t2_pools.json"):
    for r in json.load(open("data/t2_pools.json")):
        d = sum(float(p.get("totalDepositSol") or 0) for p in r["pools"])
        p_ = sum(float(p.get("pnlSol") or 0) for p in r["pools"])
        CLOSED[r["w"]] = (d, p_)


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}


def one(w):
    rows = []
    for pg in range(1, 8):
        d = get(f"{API}/portfolio/open?user={w}&page={pg}&page_size=100")
        rows += d.get("pools") or []
        if not d.get("hasNext"): break
    o_dep = sum(float(p.get("totalDepositSol") or 0) for p in rows)
    o_pnl = sum(float(p.get("pnlSol") or 0) for p in rows)
    n_pos = sum(int(p.get("openPositionCount") or 0) for p in rows)
    oor = [p for p in rows if p.get("outOfRange")]
    oor_dep = sum(float(p.get("totalDepositSol") or 0) for p in oor)
    # capital parked in pools that are out of range AND underwater: the rot
    rot = [p for p in oor if float(p.get("pnlSol") or 0) < 0]
    rot_dep = sum(float(p.get("totalDepositSol") or 0) for p in rot)
    rot_pnl = sum(float(p.get("pnlSol") or 0) for p in rot)

    if w in CLOSED:
        c_dep, c_pnl = CLOSED[w]
    else:
        cl = []
        for pg in range(1, 11):
            d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
            cl += d.get("pools") or []
            if not d.get("hasNext"): break
        c_dep = sum(float(p.get("totalDepositSol") or 0) for p in cl)
        c_pnl = sum(float(p.get("pnlSol") or 0) for p in cl)
    tot_d = c_dep + o_dep
    return {"w": w, "open_n": n_pos, "open_dep": o_dep, "open_pnl": o_pnl,
            "open_pct": o_pnl / o_dep if o_dep > 0 else 0.0,
            "closed_dep": c_dep, "closed_pnl": c_pnl,
            "closed_pct": c_pnl / c_dep if c_dep > 0 else 0.0,
            "open_share": o_dep / tot_d if tot_d > 0 else 0.0,
            "allin_pct": (c_pnl + o_pnl) / tot_d if tot_d > 0 else 0.0,
            "oor_share": oor_dep / o_dep if o_dep > 0 else 0.0,
            "rot_dep": rot_dep, "rot_pnl": rot_pnl,
            "rot_share": rot_dep / tot_d if tot_d > 0 else 0.0}


if os.path.exists(SRC):
    src = json.load(open(SRC))
    WS = [x["w"] if isinstance(x, dict) else x for x in src]
else:
    WS = [x.strip() for x in SRC.split(",") if x.strip()]
res = json.load(open(OUT)) if os.path.exists(OUT) else []
done = {r["w"] for r in res}
todo = [w for w in WS if w not in done]
print(f"  open-book screen: {len(todo):,} to do, {len(done):,} cached\n", flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(one, todo), 1):
        res.append(r)
        if i % 250 == 0:
            tmp = OUT + ".tmp"
            with open(tmp, "w") as fh: json.dump(res, fh, indent=1)
            os.replace(tmp, OUT)
            el = time.time() - t0
            print(f"    {i:,}/{len(todo):,}  {i/el:.1f}/s  "
                  f"eta {(len(todo)-i)/max(i/el,1e-9)/60:.0f} min", flush=True)
tmp = OUT + ".tmp"
with open(tmp, "w") as fh: json.dump(res, fh, indent=1)
os.replace(tmp, OUT)

res.sort(key=lambda r: r["allin_pct"] - r["closed_pct"])
print(f"  {'wallet':<46}{'open n':>7}{'open cap':>10}{'cap %':>7}{'open m2m':>10}"
      f"{'realised':>10}{'ALL-IN':>10}{'drag pp':>9}{'rot %':>7}")
for r in res[:25]:
    print(f"  {r['w']:<46}{r['open_n']:>7}{r['open_dep']:>10.1f}{100*r['open_share']:>6.1f}%"
          f"{100*r['open_pct']:>+9.1f}%{100*r['closed_pct']:>+9.2f}%{100*r['allin_pct']:>+9.2f}%"
          f"{100*(r['allin_pct']-r['closed_pct']):>+9.2f}{100*r['rot_share']:>6.1f}%")
bad = [r for r in res if r["allin_pct"] <= 0 < r["closed_pct"]]
print(f"\n  {len(bad)} of {len(res)} look profitable on realised P&L and are NOT all-in")
d = sum(r["closed_dep"] + r["open_dep"] for r in res)
print(f"  pooled realised {100*sum(r['closed_pnl'] for r in res)/sum(r['closed_dep'] for r in res):+.3f}%"
      f"   pooled ALL-IN {100*sum(r['closed_pnl']+r['open_pnl'] for r in res)/d:+.3f}%")
print(f"  median drag {100*sorted(r['allin_pct']-r['closed_pct'] for r in res)[len(res)//2]:+.3f} pp")
print(f"\n  -> {OUT}")
