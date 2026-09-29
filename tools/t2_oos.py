"""T2 -- OUT-OF-SAMPLE VALIDATION. The gate.

Everything before this ranked wallets on a window and reported that window's returns,
which is circular. This ranks on period A and scores on a DISJOINT period B.

Method
    cut date splits each wallet's pools by lastClosedAt.
    A = pools closed before the cut   -> the ranking signal
    B = pools closed after the cut    -> the score, never seen by the ranker
    Both sides measured with the same T1 vs-HODL decomposition, bounded (uncovered
    rows charged their full realised loss).

KNOWN LEAKAGE, stated because it decides how to read the result: a /portfolio row
carries a pool's LIFETIME totals stamped with its LAST close, so a B-pool that was also
worked before the cut drags some A-era P&L into B. This does NOT manufacture
correlation -- each pool address lands on exactly one side, so no row is scored twice --
it BLURS the two periods together. That makes this a conservative test: leakage pushes
measured predictive power toward the null, so a positive result here is a floor, and a
null result is genuinely ambiguous. tools/t2_exact.py removes the leakage entirely.

Controls, because a number with nothing to beat is not evidence:
    raw pnl in A -> skill in B     rule 9 says this should carry nothing
    shuffled A   -> skill in B     the null, run at the same sample size

Usage: python3 tools/t2_oos.py [CUT_DAYS_AGO=120] [MIN_POOLS_PER_SIDE=8]
"""
import json, sys, time, random, statistics as st
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

CUT_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
MIN_SIDE = int(sys.argv[2]) if len(sys.argv) > 2 else 8
NOW = int(time.time())
CUT = NOW - CUT_DAYS * 86400


def measure(pools):
    """T1 over a set of pool rows -> dict, or None if nothing computable."""
    dep = sk = 0.0
    udep = upnl = 0.0
    n = beat = unc = 0
    raw = 0.0
    for p in pools:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        raw += f(p, "pnlSol")
        r = vs_hodl(p)
        if r is None:
            unc += 1; udep += d0; upnl += f(p, "pnlSol"); continue
        v, _h, _ = r
        dep += d0; sk += v; n += 1; beat += v > 0
    if n < MIN_SIDE or dep <= 0: return None
    return {"n": n, "unc": unc, "dep": dep + udep, "skill": sk + upnl,
            "pct": (sk + upnl) / (dep + udep), "beat": beat / n, "raw": raw}


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v); i = 0
        while i < len(order):                       # average ranks over ties
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1): r[order[k]] = avg
            i = j + 1
        return r
    a, b = rank(xs), rank(ys)
    n = len(a); ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def buckets(rows, key, nb=5):
    """Sort by `key` measured in A, report what period B actually did."""
    rows = sorted(rows, key=key)
    out, size = [], len(rows) / nb
    for i in range(nb):
        chunk = rows[int(i * size):int((i + 1) * size)]
        if not chunk: continue
        dep = sum(r["B"]["dep"] for r in chunk)
        sk  = sum(r["B"]["skill"] for r in chunk)
        out.append({"n": len(chunk), "dep": dep,
                    "pooled": sk / dep if dep else 0.0,
                    "median": st.median(r["B"]["pct"] for r in chunk),
                    "beat": st.mean(r["B"]["beat"] for r in chunk),
                    "a_lo": key(chunk[0]), "a_hi": key(chunk[-1])})
    return out


def show(title, bk):
    print(f"\n  {title}")
    print(f"    {'bucket':<9}{'n':>5}{'A-signal range':>22}"
          f"{'B capital':>12}{'B pooled skill':>16}{'B median':>11}{'B beat':>9}")
    for i, b in enumerate(bk, 1):
        print(f"    Q{i:<8}{b['n']:>5}{100*b['a_lo']:>+10.2f}%..{100*b['a_hi']:>+8.2f}%"
              f"{b['dep']:>12,.0f}{100*b['pooled']:>+15.3f}%"
              f"{100*b['median']:>+10.2f}%{100*b['beat']:>8.0f}%")
    print(f"    spread Q5-Q1  {100*(bk[-1]['pooled']-bk[0]['pooled']):+.3f}%")


def bootstrap(rows, key, reps=2000, seed=7):
    """CI on the Q5-Q1 pooled-skill spread, resampling WALLETS (the unit of choice)."""
    rnd, out = random.Random(seed), []
    for _ in range(reps):
        s = [rows[rnd.randrange(len(rows))] for _ in range(len(rows))]
        b = buckets(s, key)
        if len(b) >= 2: out.append(b[-1]["pooled"] - b[0]["pooled"])
    out.sort()
    return out[int(.025 * len(out))], out[int(.5 * len(out))], out[int(.975 * len(out))]


cache = json.load(open("data/t2_pools.json"))
rows = []
for rec in cache:
    A = measure([p for p in rec["pools"] if p["t"] < CUT])
    B = measure([p for p in rec["pools"] if p["t"] >= CUT])
    if A and B: rows.append({"w": rec["w"], "A": A, "B": B})

print(f"\n  T2 OUT-OF-SAMPLE  cut {time.strftime('%Y-%m-%d', time.gmtime(CUT))} "
      f"({CUT_DAYS}d ago), min {MIN_SIDE} usable pools per side")
print(f"  {len(cache):,} wallets cached -> {len(rows):,} have both periods")
if len(rows) < 50:
    print("  NOT ENOUGH WALLETS SPAN THE CUT -- move the cut or lower MIN_SIDE"); sys.exit()

allA = sum(r["A"]["skill"] for r in rows) / sum(r["A"]["dep"] for r in rows)
allB = sum(r["B"]["skill"] for r in rows) / sum(r["B"]["dep"] for r in rows)
print(f"  population  A pooled skill {100*allA:+.3f}%   B pooled skill {100*allB:+.3f}%"
      f"   (B is the bar every bucket below must beat)")
print(f"  A capital {sum(r['A']['dep'] for r in rows):,.0f} SOL"
      f"   B capital {sum(r['B']['dep'] for r in rows):,.0f} SOL")

sA = [r["A"]["pct"] for r in rows]; sB = [r["B"]["pct"] for r in rows]
print(f"\n  Spearman(A skill, B skill)     {spearman(sA, sB):+.4f}   <- THE NUMBER")
print(f"  Spearman(A raw pnl, B skill)   "
      f"{spearman([r['A']['raw'] for r in rows], sB):+.4f}   (rule 9 control)")
print(f"  Spearman(A pools, B skill)     "
      f"{spearman([float(r['A']['n']) for r in rows], sB):+.4f}   (sample-size control)")

show("RANKED ON A's vs-HODL LP SKILL:", buckets(rows, lambda r: r["A"]["pct"]))
lo, md, hi = bootstrap(rows, lambda r: r["A"]["pct"])
print(f"    bootstrap 95% CI on that spread  [{100*lo:+.3f}%, {100*hi:+.3f}%]  median {100*md:+.3f}%")
print(f"    {'DOES NOT CLEAR ZERO' if lo <= 0 else 'CLEARS ZERO'}")

show("RANKED ON A's RAW P&L (the control every product ships):",
     buckets(rows, lambda r: r["A"]["raw"]))
lo2, _m2, hi2 = bootstrap(rows, lambda r: r["A"]["raw"])
print(f"    bootstrap 95% CI on that spread  [{100*lo2:+.3f}%, {100*hi2:+.3f}%]")

rnd = random.Random(11)
for r in rows: r["rand"] = rnd.random()      # stable key, or sorted() sees a moving target
show("RANKED AT RANDOM (the null, same n):", buckets(rows, lambda r: r["rand"]))
lo3, _m3, hi3 = bootstrap(rows, lambda r: r["rand"])
print(f"    bootstrap 95% CI on that spread  [{100*lo3:+.3f}%, {100*hi3:+.3f}%]"
      f"   <- how wide a spread pure noise produces at this n")

json.dump({"cut": CUT, "cut_days": CUT_DAYS, "min_side": MIN_SIDE,
           "n": len(rows), "spearman_skill": spearman(sA, sB),
           "spearman_rawpnl": spearman([r["A"]["raw"] for r in rows], sB),
           "pop_A": allA, "pop_B": allB,
           "spread_ci": [lo, md, hi], "rows": rows},
          open("data/t2_oos.json", "w"), indent=1)
print(f"\n  -> data/t2_oos.json")
