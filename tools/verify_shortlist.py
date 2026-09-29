"""Verify the EXACT numbers published in the shortlist, not adjacent ones.

verify_claims.py checks the data is internally consistent. That is necessary and not
sufficient: it recomputed +14.2% skill where the shortlist published +4.94%, which is a
DIFFERENT WINDOW at a DIFFERENT AGGREGATION LEVEL (365d pool rows vs period-B position
rows). A plausible explanation for a mismatched number is exactly what a fabricated
number looks like from the outside, so this reproduces the published figure itself.

Independent of the pipeline: refetches every position from the API rather than reading
data/t2_positions.json, and writes its own arithmetic. If a published number cannot be
reproduced here, the published number is wrong.

Usage: python3 tools/verify_shortlist.py [CUT_DAYS=120]
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
CUT_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
CUT = int(time.time()) - CUT_DAYS * 86400
CLAIMS = json.load(open("data/shortlist_copyable.json"))


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


def fetch_positions(w):
    """Refetch from the API. Deliberately does NOT read the project's position cache."""
    pools, pg = [], 1
    while pg <= 10:
        d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
        pools += d.get("pools") or []
        if not d.get("hasNext"): break
        pg += 1
    addrs = [p["poolAddress"] for p in pools]
    def one(pool):
        out, q = [], 1
        while q <= 5:
            d = get(f"{API}/positions/{pool}/pnl?user={w}&page={q}&page_size=100")
            out += [{**x, "pool": pool} for x in (d.get("positions") or [])]
            if not d.get("hasNext"): break
            q += 1
        return out
    with ThreadPoolExecutor(max_workers=12) as ex:
        return [x for lst in ex.map(one, addrs) for x in lst]


def skill_of(rows):
    """vs-HODL, written out longhand. Bounded: uncovered charged their full loss."""
    dep = sk = udep = upnl = 0.0; n = beat = 0
    per_pool = {}
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
        if not ok or abs(num(wd["total"]["sol"]) + num(fe["total"]["sol"]) - hodl) > 50 * d0:
            udep += d0; upnl += num(p.get("pnlSol")); continue
        v = num(wd["total"]["sol"]) + num(fe["total"]["sol"]) - hodl
        dep += d0; sk += v; n += 1; beat += v > 0
        per_pool[p["pool"]] = per_pool.get(p["pool"], 0.0) + v
    if not n or dep + udep <= 0: return None
    pos = sorted((x for x in per_pool.values() if x > 0), reverse=True)
    tot = sk + upnl
    top3 = (sum(pos[:3]) / tot) if tot > 0 else None
    excl = {k for k, _ in sorted(per_pool.items(), key=lambda kv: -kv[1])[:3]}
    e_dep = e_sk = 0.0
    for p in rows:
        if p["pool"] in excl: continue
        d0 = num(p["allTimeDeposits"]["total"]["sol"])
        if d0 <= 0: continue
        e_dep += d0
    return {"n": n, "pct": tot / (dep + udep), "beat": beat / n, "top3": top3,
            "cash": sum(num(p.get("pnlSol")) for p in rows) /
                    sum(max(num(p["allTimeDeposits"]["total"]["sol"]), 0) for p in rows)}


print(f"\n  REPRODUCING PUBLISHED SHORTLIST NUMBERS — refetched from the API, own arithmetic")
print(f"  cut {time.strftime('%Y-%m-%d', time.gmtime(CUT))} ({CUT_DAYS}d)\n")
print(f"  {'wallet':<14}{'claim A':>9}{'check A':>9}{'claim B':>9}{'check B':>9}"
      f"{'claim beat':>12}{'check':>8}{'claim n':>9}{'check':>8}   verdict")
bad = 0
for c in CLAIMS[:6]:
    w = c["w"]
    rows = fetch_positions(w)
    A = skill_of([p for p in rows if p.get("isClosed") and p.get("closedAt")
                  and p["closedAt"] < CUT])
    B = skill_of([p for p in rows if p.get("isClosed") and p.get("createdAt")
                  and p["createdAt"] >= CUT])
    if not A or not B:
        print(f"  {w[:12]:<14}  could not reproduce -- no rows one side"); bad += 1; continue
    dA, dB = abs(100*(A["pct"]-c["A"])), abs(100*(B["pct"]-c["B"]))
    dbeat = abs(100*(B["beat"]-c["beat"]))
    okk = dA < 0.5 and dB < 0.5 and dbeat < 3 and abs(B["n"]-c["Bn"]) <= max(3, 0.03*c["Bn"])
    if not okk: bad += 1
    print(f"  {w[:12]:<14}{100*c['A']:>+8.2f}%{100*A['pct']:>+8.2f}%"
          f"{100*c['B']:>+8.2f}%{100*B['pct']:>+8.2f}%"
          f"{100*c['beat']:>11.0f}%{100*B['beat']:>7.0f}%{c['Bn']:>9}{B['n']:>8}"
          f"   {'MATCH' if okk else 'MISMATCH'}", flush=True)
print(f"\n  {len(CLAIMS[:6])-bad}/{len(CLAIMS[:6])} published rows reproduce from a clean refetch")
print(f"  Any MISMATCH means the published number is wrong and must be corrected, not explained.")
