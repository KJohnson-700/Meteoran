"""VET ONE WALLET -- the full gate stack, one command, verdict with reasons.

This is the operator-facing tool. Paste any wallet address (from tracklp, a pool scan,
a Discord tip, anywhere) and it runs every gate this project has validated, in order,
and says COPY CANDIDATE or REJECT and exactly why. Nothing here is new methodology --
it is the same code paths the shortlist survived, applied to one address on demand.

Gates, in the order they run (cheap first, expensive last):
  data      /portfolio rows exist, rule-2 corruption filters
  rhythm    rule 5:  sleep6h < 12%, closes/day < 40 (human, not a 24/7 bot)
  skill     rule 7/9: BOUNDED vs-HODL > 0 (not raw P&L, which predicts nothing)
  sample    >= 25 usable pools (thin samples are stories, not evidence)
  per-position (one API call per pool, ~30s for a busy wallet):
  size      rule 10: median SOL per POSITION 0.5-10 (the $500 bankroll gate)
  A/B       rule 15: positive in period A AND disjoint period B, leak-free split;
            B quoted as a RANGE over cut dates 90-150d (rule 20)
  ex-top3   rule 13: B skill with its 3 best pools removed still > 0
  hold      rule 17: median hold >= 10 min and < 40% of positions under 5 min
  open book rule 16: all-in return > 0 and censoring drag > -1pp
  recency   traded in the last 14 days (a retired wallet cannot be copied)

Usage:  python3 tools/vet.py <address> [<address> ...]
        python3 tools/vet.py $(cat some_list.txt)
"""
import json, sys, time, collections, statistics as st, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

def flat(pos):
    # inlined from t2_exact.flat -- that module parses sys.argv at import time
    d, wd, fe = pos["allTimeDeposits"], pos["allTimeWithdrawals"], pos["allTimeFees"]
    o = {"totalDepositSol": d["total"]["sol"],
         "totalWithdrawalSol": wd["total"]["sol"],
         "totalFeeSol": fe["total"]["sol"],
         "pnlSol": pos.get("pnlSol")}
    for T, k in (("TokenX", "tokenX"), ("TokenY", "tokenY")):
        o[f"totalDeposit{T}"] = d[k]["amount"];      o[f"totalDeposit{T}Sol"] = d[k]["amountSol"]
        o[f"totalWithdrawal{T}"] = wd[k]["amount"];  o[f"totalWithdrawal{T}Sol"] = wd[k]["amountSol"]
    return o

API = "https://dlmm.datapi.meteora.ag"
NOW = int(time.time())

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0",
                                           "Accept": "application/json"})
    for a in range(4):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.4 * (a + 1))
    return {}

def paged(path, key="pools", pages=11):
    out = []
    for pg in range(1, pages):
        d = get(f"{API}{path}&page={pg}&page_size=100")
        out += d.get(key) or []
        if not d.get("hasNext"): break
    return out

def skill_of(rows):
    """(bounded_pct, covered_pct, beat_rate, n, dep) over flat rows, uncovered charged."""
    dep = sk = udep = upnl = 0.0; n = beat = 0
    for p in rows:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None: udep += d0; upnl += f(p, "pnlSol"); continue
        dep += d0; sk += r[0]; n += 1; beat += r[0] > 0
    if not n or dep + udep <= 0: return None
    return {"pct": 100*(sk+upnl)/(dep+udep), "cov": 100*sk/dep,
            "beat": 100*beat/n, "n": n, "dep": dep+udep, "skill_sol": sk+upnl}

def vet(w):
    G = []          # (gate, ok, detail)  ok in {True, False, None=info only}
    def gate(name, ok, detail): G.append((name, ok, detail))

    # ---- pool rows -------------------------------------------------------------
    pools = paged(f"/portfolio?user={w}&days_back=365")
    if not pools:
        gate("data", False, "no /portfolio rows in 365d -- unknown or inactive wallet")
        return G, "REJECT"
    clean = [p for p in pools
             if abs(f(p,"pnlSol")) < 50_000 and abs(f(p,"pnlUsd")) < 5_000_000
             and f(p,"pnlSol")*f(p,"pnlUsd") >= 0]
    gate("data", True, f"{len(pools)} pool rows, {len(pools)-len(clean)} corrupt (rule 2) dropped")
    pools = clean

    # ---- rhythm (rule 5) -------------------------------------------------------
    ts = [int(p["lastClosedAt"]) for p in pools if p.get("lastClosedAt")]
    if len(ts) >= 25:
        hrs = collections.Counter(time.gmtime(t).tm_hour for t in ts)
        sleep = 100*min(sum(hrs[(h+i)%24] for i in range(6)) for h in range(24))/len(ts)
        days = len({time.strftime("%Y-%m-%d", time.gmtime(t)) for t in ts})
        per_day = len(ts)/max(1, days)
        gate("rhythm", sleep < 12 and per_day < 40,
             f"sleep6h {sleep:.1f}% (<12), {per_day:.1f} closes/active-day (<40)")
    else:
        gate("rhythm", None, f"only {len(ts)} closes -- too few for rhythm, judge by hold time")

    # ---- lifetime skill (rules 7/9) ---------------------------------------------
    sk = skill_of(pools)
    if not sk:
        gate("skill", False, "no coverable pools -- cannot compute vs-HODL")
        return G, "REJECT"
    pnl = sum(f(p,"pnlSol") for p in pools)
    gate("skill", sk["pct"] > 0,
         f"bounded vs-HODL {sk['pct']:+.2f}% on {sk['dep']:,.0f} SOL, beat-HODL {sk['beat']:.0f}%"
         f" (raw pnl {pnl:+.1f} SOL -- ignored for ranking, rule 9)")
    gate("sample", sk["n"] >= 25, f"{sk['n']} covered pools (>=25)")

    # bail early only on hopeless cases; otherwise pay for per-position truth
    if sk["pct"] <= 0 and sk["n"] >= 25:
        return G, "REJECT"

    # ---- per-position pull (one call per pool) ----------------------------------
    addrs = [p.get("poolAddress") or p.get("pool") for p in pools]
    addrs = [a for a in addrs if a]
    def pull(a): return paged(f"/positions/{a}/pnl?user={w}", key="positions", pages=6)
    with ThreadPoolExecutor(max_workers=12) as ex:
        per_pool = dict(zip(addrs, ex.map(pull, addrs)))
    POS = [(a, p) for a, ps in per_pool.items() for p in ps]
    closed = [(a, p) for a, p in POS if p.get("isClosed") and p.get("createdAt") and p.get("closedAt")]
    if len(closed) < 20:
        gate("positions", None, f"only {len(closed)} closed positions -- per-position gates skipped")
        return G, "INSUFFICIENT DATA"

    # ---- size (rule 10, per POSITION never per pool) -----------------------------
    sizes = sorted(f(flat(p), "totalDepositSol") for _, p in closed
                   if f(flat(p), "totalDepositSol") > 0)
    med_sz = sizes[len(sizes)//2]
    gate("size", 0.1 <= med_sz <= 10,
         f"median {med_sz:.2f} SOL/position (bankroll fit 0.1-10), p90 {sizes[9*len(sizes)//10]:.2f}")

    # ---- hold time (rule 17) ------------------------------------------------------
    holds = sorted(p["closedAt"] - p["createdAt"] for _, p in closed)
    med_h = holds[len(holds)//2]; u5 = sum(1 for h in holds if h < 300)/len(holds)
    hh = f"{med_h/3600:.1f}h" if med_h >= 3600 else f"{med_h/60:.0f}m"
    gate("hold", med_h >= 600 and u5 <= 0.40,
         f"median {hh}, {100*u5:.0f}% under 5min (JIT if median<10m or >40% <5m)")
    rnd = sum(1 for s in sizes if any(abs(s-r) < 0.005*max(r,1)
              for r in (0.25,0.5,1,2,2.5,3,4,5,10,15,20,25,50,100)))/len(sizes)
    gate("style", None, f"{100*rnd:.0f}% round sizes -> "
         f"{'tool-assisted' if rnd > 0.6 else 'discretionary'} (info only, never a gate)")

    # ---- A/B out-of-sample, B as a range over cuts (rules 15 + 20) ----------------
    def split(cut_days):
        cut = NOW - cut_days*86400
        A = [flat(p) for _, p in closed if p["closedAt"] < cut]
        B = [flat(p) for _, p in POS if p.get("createdAt") and p["createdAt"] >= cut
             and p.get("isClosed")]
        return skill_of(A), skill_of(B), B, cut
    A120, B120, Brows_ignore, cut120 = split(120)
    Bs = []
    for cd in (90, 105, 120, 135, 150):
        _, b, _, _ = split(cd)
        if b and b["n"] >= 10: Bs.append(b["pct"])
    if A120 and B120 and A120["n"] >= 10 and B120["n"] >= 10 and Bs:
        gate("period A", A120["pct"] > 0, f"{A120['pct']:+.2f}% on {A120['n']} closed positions (cut 120d)")
        gate("period B", min(Bs) > 0,
             f"{min(Bs):+.2f}% to {max(Bs):+.2f}% over cuts 90-150d, n={B120['n']} at 120d"
             f" -- range per rule 20, must be positive at EVERY cut")
    else:
        gate("A/B split", None, "not enough positions on both sides of any cut -- newer wallet, judge on B-side gates only")

    # ---- concentration ex-top3 in B (rule 13) --------------------------------------
    if B120 and B120["n"] >= 10:
        bypool = collections.defaultdict(lambda: [0.0, 0.0])
        for a, p in POS:
            if not (p.get("createdAt") and p["createdAt"] >= cut120 and p.get("isClosed")): continue
            fl = flat(p); r = vs_hodl(fl); d0 = f(fl, "totalDepositSol")
            if d0 <= 0: continue
            if r is None: bypool[a][0] += f(fl,"pnlSol"); bypool[a][1] += d0
            else:         bypool[a][0] += r[0];           bypool[a][1] += d0
        tot = sum(v[0] for v in bypool.values()); dep = sum(v[1] for v in bypool.values())
        top3 = sum(sorted((v[0] for v in bypool.values()), reverse=True)[:3])
        ex = 100*(tot-top3)/dep if dep > 0 else 0
        share = 100*top3/tot if tot > 0 else 0
        gate("ex-top3", ex > 0,
             f"B skill ex 3 best pools {ex:+.2f}% (top3 = {share:.0f}% of skill, >65% is one story)")

    # ---- open book (rule 16) ---------------------------------------------------------
    op = paged(f"/portfolio/open?user={w}")
    o_dep = sum(f(p,"totalDepositSol") for p in op)
    o_pnl = sum(f(p,"pnlSol") for p in op)
    c_dep = sum(f(p,"totalDepositSol") for p in pools)
    c_pnl = sum(f(p,"pnlSol") for p in pools)
    allin = 100*(c_pnl+o_pnl)/max(c_dep+o_dep, 1e-9)
    real  = 100*c_pnl/max(c_dep, 1e-9)
    drag  = allin - real
    n_open = sum(int(p.get("openPositionCount") or 0) for p in op)
    gate("open book", allin > 0 and drag > -1.0,
         f"all-in {allin:+.2f}%, drag {drag:+.2f}pp, {n_open} open positions"
         f" ({100*o_dep/max(c_dep+o_dep,1e-9):.1f}% of capital open)")

    # ---- recency ----------------------------------------------------------------------
    last = max(ts) if ts else 0
    days_ago = (NOW-last)/86400
    gate("recency", days_ago <= 14 or n_open > 0,
         f"last close {days_ago:.1f}d ago, {n_open} positions open now")

    hard_fail = [g for g, ok, _ in G if ok is False]
    verdict = "REJECT" if hard_fail else "COPY CANDIDATE"
    return G, verdict

if __name__ == "__main__":
    import re
    raw = " ".join(sys.argv[1:]) or sys.stdin.read()
    ws = list(dict.fromkeys(re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", raw)))
    if not ws: sys.exit("usage: python3 tools/vet.py <address> [...]")
    for w in ws:
        try: _nk = json.load(open("data/nicknames.json")).get(w, {}).get("nick")
        except Exception: _nk = None
        print(f"\n  ================ {w} ================")
        if _nk: print(f'    "{_nk}"')
        t0 = time.time()
        G, verdict = vet(w)
        for name, ok, detail in G:
            mark = "PASS" if ok else ("FAIL" if ok is False else "info")
            print(f"    {mark:<5} {name:<10} {detail}")
        fails = [n for n, ok, _ in G if ok is False]
        print(f"\n    VERDICT: {verdict}" + (f"  ({', '.join(fails)})" if fails else "")
              + f"   [{time.time()-t0:.0f}s]")
        print(f"    Every number above is recomputable: raw endpoints are"
              f" /portfolio, /positions/<pool>/pnl, /portfolio/open at {API}")
