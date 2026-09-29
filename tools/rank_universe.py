"""Rank the screened universe. Applies the rule-2 corruption filters, then the rule-5
rhythm proxy, then reports what survives.

Filters, in order, each one counted so the attrition is visible:
  corrupt : |pnl_sol|<50k, |pnl_usd|<5M, pct_sol>-1.0, |pct_sol|<10, pnl_sol*pnl_usd>=0
  inactive: needs enough closed positions to say anything at all
  machine : position count alone is a tell (22,888 closed positions is a machine)

Output is a CANDIDATE list for the expensive per-pool pull, not a recommendation.
Nothing here is out-of-sample (T2) and nothing here has vs-HODL (T1) yet.
"""
import json, sys, statistics as st

MIN_CLOSED = int(sys.argv[1]) if len(sys.argv) > 1 else 20
MAX_CLOSED = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
TOP        = int(sys.argv[3]) if len(sys.argv) > 3 else 40

rows = json.load(open("data/dlmm_pnl.json"))

def ok(r):
    return (abs(r["pnl_sol"]) < 50_000 and abs(r["pnl_usd"]) < 5_000_000
            and r["pct_sol"] > -1.0 and abs(r["pct_sol"]) < 10
            and r["pnl_sol"] * r["pnl_usd"] >= 0)

clean   = [r for r in rows if ok(r)]
active  = [r for r in clean if r["closed"] >= MIN_CLOSED]
human   = [r for r in active if r["closed"] <= MAX_CLOSED]
winners = [r for r in human if r["pnl_sol"] > 0]

print(f"\n  screened          {len(rows):,}")
print(f"  passed corruption {len(clean):,}   ({100*(1-len(clean)/max(len(rows),1)):.1f}% junk — rule 2)")
print(f"  >= {MIN_CLOSED} closes      {len(active):,}")
print(f"  <= {MAX_CLOSED} closes    {len(human):,}   (position count as a machine tell — rule 5)")
print(f"  profitable        {len(winners):,}   ({100*len(winners)/max(len(human),1):.1f}% of them)")

if clean:
    agg = sum(r["pnl_sol"] for r in clean)
    print(f"\n  AGGREGATE across {len(clean):,} sanity-checked wallets: {agg:+,.0f} SOL")
    print(f"  median {st.median([r['pnl_sol'] for r in clean]):+.2f} SOL — "
          f"the uncomfortable prior: most make a little, a few are destroyed")

cands = sorted(human, key=lambda r: -r["pnl_sol"])[:TOP]
print(f"\n  top {len(cands)} candidates by pnl_sol (NOT a recommendation — no T1, no T2)\n")
print(f"  {'#':>3} {'wallet':<44} {'pnl SOL':>10} {'pct_sol':>8} {'closed':>7} {'open':>6}")
for i, r in enumerate(cands, 1):
    print(f"  {i:>3} {r['w']:<44} {r['pnl_sol']:>+10,.1f} {100*r['pct_sol']:>7.1f}% "
          f"{r['closed']:>7,} {r['open']:>6,}")

json.dump(cands, open("data/candidates.json", "w"), indent=1)
print(f"\n  -> data/candidates.json")
