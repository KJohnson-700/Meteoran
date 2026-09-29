"""T2 EXACT -- per-POSITION out-of-sample, no period leakage.

t2_oos.py splits /portfolio rows, whose totals are a pool's LIFETIME stamped with its
last close, so a pool worked on both sides of the cut drags old P&L into the new period.
This uses /positions/{pool}/pnl?user=, which returns one row PER POSITION with createdAt
AND closedAt, so a position can be placed in a period without ambiguity:

    A  closedAt  <  CUT                      ranked on
    B  createdAt >= CUT                      scored on, opened entirely after the cut
    straddlers   createdAt < CUT <= closedAt  DROPPED and counted, never assigned

Costs one API call per (wallet, pool), so this is for finalists only -- feed it the
wallets that survive t2_oos.py, not the leaderboard.

Usage: python3 tools/t2_exact.py [CUT_DAYS=120] [wallets.json|addr,addr,...]
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

CUT_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
CUT = int(time.time()) - CUT_DAYS * 86400
API = "https://dlmm.datapi.meteora.ag"
OUT = "data/t2_exact.json"
POSCACHE = "data/t2_positions.json"
CACHE, POS, DIRTY = [], {}, [0]        # filled by main(); import must stay cheap


def save(obj, path, indent=None):
    """Write via a temp file and rename. A kill during a plain json.dump leaves a
    truncated file that nothing can parse, and the cache is expensive to rebuild."""
    tmp = path + ".tmp"
    with open(tmp, "w") as fh: json.dump(obj, fh, indent=indent)
    os.replace(tmp, path)


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                             "Accept": "application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}


def flat(pos):
    """Position JSON -> the flat shape vs_hodl() already knows how to read."""
    d, wd, fe = pos["allTimeDeposits"], pos["allTimeWithdrawals"], pos["allTimeFees"]
    o = {"totalDepositSol": d["total"]["sol"],
         "totalWithdrawalSol": wd["total"]["sol"],
         "totalFeeSol": fe["total"]["sol"],
         "pnlSol": pos.get("pnlSol")}
    for T, k in (("TokenX", "tokenX"), ("TokenY", "tokenY")):
        o[f"totalDeposit{T}"] = d[k]["amount"];      o[f"totalDeposit{T}Sol"] = d[k]["amountSol"]
        o[f"totalWithdrawal{T}"] = wd[k]["amount"];  o[f"totalWithdrawal{T}Sol"] = wd[k]["amountSol"]
    return o


def positions(w, pool):
    out = []
    for pg in range(1, 6):
        d = get(f"{API}/positions/{pool}/pnl?user={w}&page={pg}&page_size=100")
        out += d.get("positions") or []
        if not d.get("hasNext"): break
    return out


def measure(rows):
    dep = sk = 0.0; udep = upnl = 0.0; n = beat = unc = 0
    for p in rows:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None:
            unc += 1; udep += d0; upnl += f(p, "pnlSol"); continue
        v, _h, _ = r
        dep += d0; sk += v; n += 1; beat += v > 0
    if not n: return None
    return {"n": n, "unc": unc, "dep": dep + udep, "skill": sk + upnl,
            "pct": (sk + upnl) / (dep + udep), "beat": beat / n,
            "avg_pos": (dep + udep) / (n + unc)}


def one(w):
    pools = [p["p"] for p in next((r["pools"] for r in CACHE if r["w"] == w), [])]
    if not pools:                                   # not in the T2 cache -- pull fresh
        rows = []
        for pg in range(1, 11):
            d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
            rows += d.get("pools") or []
            if not d.get("hasNext"): break
        pools = [p["poolAddress"] for p in rows]
    cached = POS.get(w)
    if cached is not None:
        allpos = cached
    else:
        with ThreadPoolExecutor(max_workers=12) as ex:
            allpos = [{**p, "_pool": q} for q, lst in
                      zip(pools, ex.map(lambda x: positions(w, x), pools)) for p in lst]
        POS[w] = allpos
        DIRTY[0] += 1
        if DIRTY[0] % 10 == 0: save(POS, POSCACHE)
    A, B, straddle, open_now = [], [], 0, 0
    bypool = {}
    for p in allpos:
        c, x = p.get("createdAt"), p.get("closedAt")
        if not p.get("isClosed") or not x: open_now += 1; continue
        if not c: continue
        fl = flat(p)
        if x < CUT: A.append(fl)
        elif c >= CUT:
            B.append(fl); bypool.setdefault(p.get("_pool", "?"), []).append(fl)
        else: straddle += 1
    # RULE 13, applied out of sample: skill that lives in 3 pools is one token's story.
    # Measured on B only -- concentration in the SCORED period is what would actually
    # have been copied, and it is the number the lifetime version cannot see.
    ps = sorted((sum(vs_hodl(x)[0] for x in v if vs_hodl(x)) for v in bypool.values()),
                reverse=True)
    mB = measure(B)
    tot = mB["skill"] if mB else 0.0
    # >100% means the pools outside the top 3 lost money on net; None means total skill
    # was negative, which makes the share meaningless rather than zero.
    top3 = 100 * sum(p for p in ps[:3] if p > 0) / tot if tot > 0 else None
    ex3 = measure([x for k, v in bypool.items() for x in v
                   if k not in {k2 for k2, v2 in sorted(
                       bypool.items(),
                       key=lambda kv: -sum(vs_hodl(x)[0] for x in kv[1] if vs_hodl(x)))[:3]}])
    return {"w": w, "pools": len(pools), "positions": len(allpos),
            "straddle": straddle, "open": open_now, "b_pools": len(bypool),
            "B_top3": top3, "B_ex_top3": ex3["pct"] if ex3 else None,
            "A": measure(A), "B": mB}


def main():
    arg = sys.argv[2] if len(sys.argv) > 2 else "data/t2_survivors.json"
    if os.path.exists(arg):
        src = json.load(open(arg))
        WS = [x["w"] if isinstance(x, dict) else x for x in src]
    else:
        WS = [x.strip() for x in arg.split(",") if x.strip()]
    global CACHE, POS
    CACHE = json.load(open("data/t2_pools.json")) if os.path.exists("data/t2_pools.json") else []
    POS = json.load(open(POSCACHE)) if os.path.exists(POSCACHE) else {}

    print(f"  T2 EXACT  cut {time.strftime('%Y-%m-%d', time.gmtime(CUT))} ({CUT_DAYS}d ago)"
          f"  {len(WS)} wallets\n")
    print(f"  {'wallet':<46}{'strdl':>6}{'A n':>6}{'A skill':>10}{'B n':>6}{'B skill':>10}"
          f"{'B beat':>8}{'SOL/pos':>9}{'B pools':>9}{'top3':>7}{'ex-top3':>9}")
    res = []
    for w in WS:
        r = one(w); res.append(r)
        A, B = r["A"], r["B"]
        e = r["B_ex_top3"]
        print(f"  {w:<46}{r['straddle']:>6}"
              f"{(A['n'] if A else 0):>6}{(100*A['pct'] if A else 0):>+9.2f}%"
              f"{(B['n'] if B else 0):>6}{(100*B['pct'] if B else 0):>+9.2f}%"
              f"{(100*B['beat'] if B else 0):>7.0f}%{(B['avg_pos'] if B else 0):>9.2f}"
              f"{r['b_pools']:>9}"
              f"{(f'{r[chr(66)+chr(95)+chr(116)+chr(111)+chr(112)+chr(51)]:.0f}%' if r['B_top3'] is not None else 'n/a'):>7}"
              f"{(f'{100*e:+.2f}%' if e is not None else '   --'):>9}", flush=True)
    save(res, OUT, indent=1)
    save(POS, POSCACHE)

    ok = [r for r in res if r["A"] and r["B"] and r["A"]["n"] >= 10 and r["B"]["n"] >= 10]
    if ok:
        dA = sum(r["A"]["dep"] for r in ok); dB = sum(r["B"]["dep"] for r in ok)
        print(f"\n  {len(ok)} wallets with >=10 positions each side")
        print(f"  pooled A skill {100*sum(r['A']['skill'] for r in ok)/dA:+.3f}%"
              f"   pooled B skill {100*sum(r['B']['skill'] for r in ok)/dB:+.3f}%")
        held = [r for r in ok if r["A"]["pct"] > 0 and r["B"]["pct"] > 0]
        print(f"  positive in A AND held positive in B: {len(held)}/{len(ok)}")
    print(f"\n  -> {OUT}")


if __name__ == "__main__":
    main()
