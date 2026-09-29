"""How much of a target's edge actually survives being COPIED?

Every number in this project backtests the SELECTION rule. None of them tests execution.
A copier does not get the target's fill -- they learn of a position after it is on chain,
react, and enter late. This measures that haircut retrospectively, so the answer does not
have to wait weeks.

Deliberately NO bin math. CLAUDE.md is explicit that rebuilding DLMM mechanics is weeks of
work for no edge, so this measures only what position metadata and 5m candles already
say:

  catchable   is the position still OPEN at entry + delay? If the target held it 90
              seconds, a copier polling once a minute never gets in at all.
  drift       DELTA in "price inside the target's own [minPrice,maxPrice]" between a
              zero-delay entry and a delayed one. The LEVEL is useless and was quoted
              wrongly once: at ZERO delay only 60-76% of entries are in range, because
              (a) 5m closes cannot resolve the entry instant and (b) placing one-sided
              liquidity just outside the current price is a normal DLMM strategy, not a
              failure. Only the zero-delay-vs-delayed DIFFERENCE is a copy cost, and it
              measures 0 to -2pp at five minutes.
  life left   what share of the position's life remains after the delay -- fees accrue
              over time, so this is the first-order haircut on the edge.

`edge_kept` = catchable x life_left x (1 + drift): the share of the target's fee-earning
window a copier at that delay captures. UPPER bound -- ignores slippage, rent, and the
fact that the remaining window need not earn at the same rate as the whole.

Usage: python3 tools/paper_replay.py [wallets.json|addr,...] [MAX_POS_PER_WALLET=250]
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
DELAYS = (60, 300, 900, 1800, 3600)          # 1m, 5m, 15m, 30m, 60m
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/shortlist_copyable.json"
MAXP = int(sys.argv[2]) if len(sys.argv) > 2 else 250
POS = json.load(open("data/t2_positions.json"))


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}


def price_at(pool, t):
    """Close of the 5m candle containing t. 1m is rejected by the API."""
    d = get(f"{API}/pools/{pool}/ohlcv?timeframe=5m&start_time={t-900}&end_time={t+900}")
    rows = d.get("data") or []
    best = None
    for r in rows:
        ts = int(r.get("timestamp") or 0)
        if ts <= t and (best is None or ts > best[0]): best = (ts, r)
    return float(best[1]["close"]) if best else None


def one(w):
    ps = [p for p in POS.get(w, []) if p.get("isClosed")
          and p.get("createdAt") and p.get("closedAt")
          and p.get("minPrice") and p.get("maxPrice") and p.get("_pool")]
    ps.sort(key=lambda p: -p["closedAt"])
    ps = ps[:MAXP]
    if len(ps) < 30: return None

    # Stage 1 is free: can a copier even get in before the target is out?
    out = {"w": w, "n": len(ps), "delays": {}}
    for d in DELAYS:
        alive = [p for p in ps if p["closedAt"] - p["createdAt"] > d]
        life = [1 - d / (p["closedAt"] - p["createdAt"]) for p in alive]
        out["delays"][d] = {"catchable": len(alive) / len(ps),
                            "life_left": (sum(life) / len(life)) if life else 0.0}

    # Stage 2 needs the ZERO-DELAY CONTROL as well as the delayed measurement, or the
    # in-range level gets mistaken for a copy cost. Only the difference is one.
    probe = [p for p in ps if p["closedAt"] - p["createdAt"] > 1800][:100]
    def chk(args):
        p, d = args
        v = price_at(p["_pool"], p["createdAt"] + d)
        if v is None: return None
        return float(p["minPrice"]) <= v <= float(p["maxPrice"])
    rates = {}
    for d in (0, 300):
        with ThreadPoolExecutor(max_workers=10) as ex:
            r = [x for x in ex.map(chk, [(p, d) for p in probe]) if x is not None]
        rates[d] = (sum(r) / len(r)) if r else None
    out["in_range_0m"], out["in_range_5m"] = rates[0], rates[300]
    out["drift_5m"] = (rates[300] - rates[0]) if (rates[0] and rates[300]) else None
    out["probed"] = len(probe)
    return out


if os.path.exists(SRC):
    src = json.load(open(SRC))
    WS = [x["w"] if isinstance(x, dict) else x for x in src]
else:
    WS = [x.strip() for x in SRC.split(",") if x.strip()]

print(f"  copy-delay replay on {len(WS)} wallets, up to {MAXP} recent positions each\n")
print(f"  {'wallet':<46}{'n':>5}" + "".join(f"{str(d//60)+'m':>17}" for d in DELAYS))
print(f"  {'':<46}{'':>5}" + "".join(f"{'catch/life':>17}" for _ in DELAYS))
res = []
for w in WS:
    r = one(w)
    if not r: continue
    res.append(r)
    row = "".join(f"{100*r['delays'][d]['catchable']:>9.0f}%"
                  f"{100*r['delays'][d]['life_left']:>7.0f}%" for d in DELAYS)
    print(f"  {w:<46}{r['n']:>5}{row}", flush=True)
json.dump(res, open("data/paper_replay.json", "w"), indent=1)

print(f"\n  EDGE KEPT at a 5-minute copy delay. `in-range @0m` is the CONTROL -- the same")
print(f"  measurement with no delay at all; only the drift between them is a copy cost.")
print(f"  {'wallet':<46}{'probed':>8}{'@0m':>7}{'@5m':>7}{'drift':>8}"
      f"{'catch':>7}{'life':>7}{'EDGE KEPT':>11}")
for r in res:
    dr = r.get("drift_5m")
    if dr is None: continue
    d = r["delays"][300]
    kept = d["catchable"] * d["life_left"] * (1 + dr)
    r["edge_kept_5m"] = kept
    print(f"  {r['w']:<46}{r['probed']:>8}{100*r['in_range_0m']:>6.0f}%"
          f"{100*r['in_range_5m']:>6.0f}%{100*dr:>+7.0f}pp{100*d['catchable']:>6.0f}%"
          f"{100*d['life_left']:>6.0f}%{100*kept:>10.0f}%")
json.dump(res, open("data/paper_replay.json", "w"), indent=1)
print(f"\n  UPPER bound: no slippage, no rent, and it assumes the remaining window earns")
print(f"  at the same rate as the whole.")
