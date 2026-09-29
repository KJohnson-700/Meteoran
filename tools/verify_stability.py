"""How much does a published number move when an arbitrary choice moves?

verify_shortlist.py could not reproduce 2 of 6 published rows. The first explanation --
time drift in a NOW-relative cut -- was tested by shifting the cut a day and got WORSE
(3/6). So the question is not "is the data real" but "is the number STABLE", and false
precision is its own kind of ghost data: +4.94% reads as measured to two decimals when
the choice of cut date alone may move it by a point.

Fetch each wallet's positions ONCE, then re-split across many cut dates in memory. Report
the RANGE. Any figure quoted from this pipeline should carry that range, not a point.
"""
import json, sys, time, statistics as st, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
CUTS = list(range(90, 156, 5))
CLAIMS = json.load(open("data/shortlist_copyable.json"))[:6]
NOW = int(time.time())


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=30) as x: return json.loads(x.read())
        except Exception: time.sleep(0.4 * (a + 1))
    return {}


def num(v):
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0


def fetch(w):
    pools, pg = [], 1
    while pg <= 10:
        d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
        pools += d.get("pools") or []
        if not d.get("hasNext"): break
        pg += 1
    def one(pool):
        out, q = [], 1
        while q <= 5:
            d = get(f"{API}/positions/{pool}/pnl?user={w}&page={q}&page_size=100")
            out += [{**x, "pool": pool} for x in (d.get("positions") or [])]
            if not d.get("hasNext"): break
            q += 1
        return out
    with ThreadPoolExecutor(max_workers=12) as ex:
        return [x for lst in ex.map(one, [p["poolAddress"] for p in pools]) for x in lst]


def skill(rows):
    dep = sk = udep = upnl = 0.0; n = 0
    for p in rows:
        d = p["allTimeDeposits"]; wd = p["allTimeWithdrawals"]; fe = p["allTimeFees"]
        d0 = num(d["total"]["sol"])
        if d0 <= 0: continue
        hodl = 0.0; ok = True
        for k in ("tokenX", "tokenY"):
            da = num(d[k]["amount"])
            if da <= 0: continue
            wa, ws, ds = num(wd[k]["amount"]), num(wd[k]["amountSol"]), num(d[k]["amountSol"])
            if wa <= 0 or ws <= 0 or ds <= 0: ok = False; break
            hodl += da * (ws / wa)
        v = (num(wd["total"]["sol"]) + num(fe["total"]["sol"]) - hodl) if ok else None
        if v is None or abs(v) > 50 * d0:
            udep += d0; upnl += num(p.get("pnlSol")); continue
        dep += d0; sk += v; n += 1
    return ((sk + upnl) / (dep + udep), n) if (dep + udep) > 0 and n else (None, 0)


print(f"\n  STABILITY OF THE PUBLISHED B-SKILL under the choice of cut date")
print(f"  cuts swept: {CUTS[0]}d to {CUTS[-1]}d in 5-day steps\n")
print(f"  {'wallet':<14}{'published':>11}{'min':>9}{'median':>9}{'max':>9}"
      f"{'spread':>9}{'n range':>14}   honest quote")
out = []
for c in CLAIMS:
    rows = fetch(c["w"])
    vals, ns = [], []
    for cd in CUTS:
        cut = NOW - cd * 86400
        v, n = skill([p for p in rows if p.get("isClosed") and p.get("createdAt")
                      and p["createdAt"] >= cut])
        if v is not None: vals.append(v); ns.append(n)
    if len(vals) < 5: continue
    lo, hi, md = min(vals), max(vals), st.median(vals)
    out.append({"w": c["w"], "published": c["B"], "min": lo, "max": hi, "median": md})
    print(f"  {c['w'][:12]:<14}{100*c['B']:>+10.2f}%{100*lo:>+8.2f}%{100*md:>+8.2f}%"
          f"{100*hi:>+8.2f}%{100*(hi-lo):>8.2f}p{min(ns):>7}-{max(ns):<6}"
          f"   {100*lo:+.1f}% to {100*hi:+.1f}%", flush=True)
json.dump(out, open("data/verify_stability.json", "w"), indent=1)
if out:
    sp = sorted(r["max"] - r["min"] for r in out)
    print(f"\n  median spread across cut dates: {100*sp[len(sp)//2]:.2f} percentage points")
    inside = sum(1 for r in out if r["min"] <= r["published"] <= r["max"])
    print(f"  published value falls inside its own range: {inside}/{len(out)}")
    print(f"\n  -> quote RANGES. A two-decimal B-skill is false precision when the cut")
    print(f"     date alone moves it by {100*sp[len(sp)//2]:.1f}pp. The RANKING is what T2")
    print(f"     validated (rho +0.38 out of sample); the second decimal was never real.")
