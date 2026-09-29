"""A bot tell the rhythm filter structurally cannot see.

rule 5 measures rhythm from `lastClosedAt` -- one timestamp PER POOL. It catches a wallet
that trades around the clock. It cannot catch a wallet that trades in human hours and
holds each position for ninety seconds, because pool-level timestamps carry no duration.

Per-POSITION data does. Two signals, both from the cache t2_exact already builds:
  hold      median seconds from createdAt to closedAt. A JIT / single-swap liquidity bot
            sits under a few minutes. The operator's own described rhythm is 15-24 HOURS.
  round     share of deposits landing on a round number (0.5/1/2/5/10/25/50/100 SOL).

CAREFUL WITH `round`. The operator will himself run Valhalla with preset position sizes,
so round sizing is what a TOOL-ASSISTED HUMAN looks like, not what disqualifies one.
Treating it as a bot tell would reject the exact profile he is trying to become. The gate
that actually matters is DURATION: nobody chooses a pool, deploys and exits inside two
minutes, a thousand times over. That is JIT / single-swap liquidity -- latency-bound,
bundle-dependent, and not reproducible through Valhalla at any bankroll.

  JIT        median hold < 10 min, or >40% of positions under 5 min -> UNCOPYABLE
  fast tool  minutes-to-hours, often round sizes -> fine, this is the target profile
"""
import json, sys, statistics as st

POS = json.load(open("data/t2_positions.json"))
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/shortlist_ranked.json"
ROUND = (0.25, 0.5, 1, 2, 2.5, 3, 4, 5, 10, 15, 20, 25, 50, 100)

def tells(w):
    ps = [p for p in POS.get(w, []) if p.get("isClosed")
          and p.get("createdAt") and p.get("closedAt")]
    if len(ps) < 20: return None
    holds = sorted(p["closedAt"] - p["createdAt"] for p in ps)
    sizes = [float(p["allTimeDeposits"]["total"]["sol"] or 0) for p in ps]
    sizes = [s for s in sizes if s > 0]
    rnd = sum(1 for s in sizes if any(abs(s - r) < 0.005 * max(r, 1) for r in ROUND))
    return {"n": len(ps), "med_s": holds[len(holds)//2],
            "p10_s": holds[len(holds)//10],
            "under5m": sum(1 for h in holds if h < 300) / len(holds),
            "under1h": sum(1 for h in holds if h < 3600) / len(holds),
            "round": rnd / max(len(sizes), 1),
            "uniq_sizes": len({round(s, 3) for s in sizes}) / max(len(sizes), 1)}

rows = json.load(open(SRC))
print(f"  {'wallet':<46}{'n':>6}{'median hold':>13}{'p10':>10}{'<5min':>8}{'<1h':>7}"
      f"{'round sz':>10}{'uniq sz':>9}  verdict")
out = []
for r in rows:
    w = r["w"] if isinstance(r, dict) else r
    t = tells(w)
    if not t: continue
    def fmt(s):
        return f"{s}s" if s < 120 else (f"{s/60:.0f}m" if s < 7200 else f"{s/3600:.1f}h")
    bot = t["med_s"] < 600 or t["under5m"] > 0.4        # JIT only; see the docstring
    out.append({**(r if isinstance(r, dict) else {"w": w}), **t, "machine": bot})
    print(f"  {w:<46}{t['n']:>6}{fmt(t['med_s']):>13}{fmt(t['p10_s']):>10}"
          f"{100*t['under5m']:>7.0f}%{100*t['under1h']:>6.0f}%{100*t['round']:>9.0f}%"
          f"{100*t['uniq_sizes']:>8.0f}%  "
          f"{'JIT - UNCOPYABLE' if bot else ('tool-assisted' if t['round'] > 0.6 else 'discretionary')}")
keep = [r for r in out if not r["machine"]]
json.dump(out, open("data/hold_tells.json", "w"), indent=1)
print(f"\n  {len(keep)} of {len(out)} are copyable through Valhalla "
      f"({len(out)-len(keep)} are JIT / sub-10-minute strategies)")
json.dump(keep, open("data/shortlist_copyable.json", "w"), indent=1)
print(f"  -> data/shortlist_copyable.json")
