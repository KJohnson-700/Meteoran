"""RULE 14, finally closed: skill is measured per CYCLE, never per year.

A wallet earning +4% per cycle at one cycle a week loses to one earning +0.5% six times a
day. Every number in this project is per cycle, so none of them is a return. Closing it
needs capital utilisation, and the per-position cache has what that takes: each position's
size, start, end and realised vs-HODL.

Simulate a follower with a fixed bankroll walking the target's positions in time order:
  - mirror a position only if free capital allows it, at min(target size, bankroll/slots)
  - hold for the target's own duration, then free the capital
  - credit the target's realised vs-HODL on that position, times the copy haircut from
    tools/paper_replay.py (what survives a 5-minute delay)

RUN IT OUT OF SAMPLE OR IT IS WORTHLESS. The first run of this tool replayed the last
120 days on wallets that had been SELECTED on the last 120 days and printed +60,509%
annualised. That is rule 8 one level up: simulating the window that picked the wallets.
Pass a selection list built only from data older than the simulated window --
`data/t2_abc.json` holds one (its rule reads periods A and B, both older than 120 days).

SANITY ANCHOR: the TARGET'S OWN PERIOD return -- its P&L over its AVERAGE DEPLOYED
CAPITAL, which is sum(size x duration)/span. Do NOT divide by the sum of deposits: that
is capital TURNOVER, and dividing by it yields a PER-CYCLE rate that is not comparable to
the follower's period return. Getting that wrong made the follower look 3x better than
the target it was copying.

THE RESULT IS TAIL-DRIVEN AND A POINT ESTIMATE IS MISLEADING. A median 71% of the
follower's P&L comes from its five best positions. With one bankroll you either catch
those or you do not, so this reports a BOOTSTRAP DISTRIBUTION over which positions get
caught, not a single number.

Other caveats it still inherits: rule 11 (the level is real but small), rule 16 (open
positions are excluded, so this is the realised-only view).

Usage: python3 tools/follow_sim.py [BANKROLL=5] [SLOTS=3] [DAYS=120] [SELECTION.json]
"""
import json, sys, time, statistics as st
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

BANK = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
SLOTS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
DAYS = int(sys.argv[3]) if len(sys.argv) > 3 else 120
NOW = int(time.time()); T0 = NOW - DAYS * 86400
POS = json.load(open("data/t2_positions.json"))
# Copy haircut. DELAY_S=300 was the pre-measurement assumption; the forward recorder
# (rule 21) measured actual detection lag at median 38s / max 63s over n=42, so the
# 60-second replay column is the evidenced default. keep = catchable x life_left.
DELAY_S = sys.argv[5] if len(sys.argv) > 5 else "60"
KEEP = {}
for r in json.load(open("data/paper_replay.json")):
    d = r.get("delays", {}).get(DELAY_S)
    KEEP[r["w"]] = (d["catchable"] * d["life_left"]) if d else r.get("edge_kept_5m", 0.85)


def flat(p):
    d, wd, fe = p["allTimeDeposits"], p["allTimeWithdrawals"], p["allTimeFees"]
    o = {"totalDepositSol": d["total"]["sol"], "totalWithdrawalSol": wd["total"]["sol"],
         "totalFeeSol": fe["total"]["sol"], "pnlSol": p.get("pnlSol")}
    for T, k in (("TokenX", "tokenX"), ("TokenY", "tokenY")):
        o[f"totalDeposit{T}"] = d[k]["amount"];     o[f"totalDeposit{T}Sol"] = d[k]["amountSol"]
        o[f"totalWithdrawal{T}"] = wd[k]["amount"]; o[f"totalWithdrawal{T}Sol"] = wd[k]["amountSol"]
    return o


def sim(w):
    ps = []
    for p in POS.get(w, []):
        if not (p.get("isClosed") and p.get("createdAt") and p.get("closedAt")): continue
        if p["createdAt"] < T0: continue
        fl = flat(p); dep = f(fl, "totalDepositSol")
        if dep <= 0: continue
        # CASH, not skill. vs-HODL is LP value minus HODL value: a position can be
        # +10% vs-HODL while losing 80% in SOL because the token collapsed. A follower
        # banks SOL. vs-HODL selects the wallet; pnlSol is what the wallet pays.
        r = vs_hodl(fl)
        cash = f(fl, "pnlSol") / dep
        skill = (r[0] / dep) if r else cash
        ps.append((p["createdAt"], p["closedAt"], dep, cash, skill))
    if len(ps) < 20: return None
    ps.sort()
    keep = KEEP.get(w, 0.85)
    slot_sz = BANK / SLOTS
    free, busy = BANK, []          # busy = [(release_time, amount)]
    taken = skipped = 0
    pnl = 0.0; deployed_seconds = 0.0
    for c, x, dep, pct, _sk in ps:
        busy.sort()
        while busy and busy[0][0] <= c:
            free += busy.pop(0)[1]
        size = min(dep, slot_sz)
        if size > free + 1e-9:
            skipped += 1; continue
        free -= size; busy.append((x, size))
        taken += 1
        pnl += size * pct * keep
        deployed_seconds += size * (x - c)
    # ANCHOR: target's PERIOD return = P&L / average capital deployed over the window.
    span0 = NOW - T0
    t_avg_cap = sum(d * (x - c) for c, x, d, _, _ in ps) / span0
    t_pnl = sum(d * p for _, _, d, p, _ in ps)
    t_ret = t_pnl / t_avg_cap if t_avg_cap > 0 else 0.0
    t_turn = sum(d for _, _, d, _, _ in ps)
    t_cycle = t_pnl / t_turn
    t_skill = sum(d * k for _, _, d, _, k in ps) / t_turn
    # and how concentrated the follower's P&L is -- a few monster positions is not a rate
    contrib = sorted((min(d, BANK / SLOTS) * p * keep for _, _, d, p, _ in ps), reverse=True)
    span = (NOW - T0)
    util = deployed_seconds / (BANK * span)
    ret = pnl / BANK
    ann = ((1 + ret) ** (365 / DAYS) - 1) if ret > -1 else -1
    top5 = sum(c for c in contrib[:5] if c > 0) / pnl if pnl > 0 else None
    return {"w": w, "n": len(ps), "taken": taken, "skipped": skipped,
            "keep": keep, "util": util, "pnl_sol": pnl, "ret": ret, "ann": ann,
            "cycles_per_day": taken / DAYS, "target_ret": t_ret,
            "target_cycle": t_cycle, "target_skill": t_skill,
            "target_avg_cap": t_avg_cap, "top5": top5,
            "taken_pcts": [(min(d, slot_sz), p) for _, _, d, p, _ in ps],
            "med_size": st.median(min(d, slot_sz) for _, _, d, _, _ in ps)}


SEL = sys.argv[4] if len(sys.argv) > 4 else "data/shortlist_copyable.json"
src = json.load(open(SEL))
rows = src["selected"] if isinstance(src, dict) and "selected" in src else src
print(f"\n  FOLLOW SIMULATION  bankroll {BANK:.0f} SOL, {SLOTS} concurrent slots "
      f"({BANK/SLOTS:.2f} SOL each), last {DAYS} days")
print(f"  per-position outcomes are the TARGET'S OWN realised vs-HODL, haircut by the")
print(f"  5-minute copy factor from tools/paper_replay.py\n")
print(f"  selection list: {SEL}")
print(f"  {'wallet':<46}{'offered':>8}{'taken':>7}{'util':>7}{'cyc/d':>7}"
      f"{'follower':>10}{'TARGET':>9}{'cash/cyc':>10}{'skill/cyc':>11}{'top5':>7}")
out = []
for r in rows:
    s = sim(r["w"] if isinstance(r, dict) else r)
    if not s: continue
    out.append(s)
    t5 = f"{100*s['top5']:.0f}%" if s['top5'] is not None else "n/a"
    print(f"  {s['w']:<46}{s['n']:>8}{s['taken']:>7}{100*s['util']:>6.0f}%"
          f"{s['cycles_per_day']:>7.1f}{100*s['ret']:>+9.1f}%{100*s['target_ret']:>+8.1f}%"
          f"{100*s['target_cycle']:>+9.2f}%{100*s['target_skill']:>+10.2f}%{t5:>7}")
json.dump(out, open("data/follow_sim.json", "w"), indent=1)
if out:
    rets = sorted(r["ret"] for r in out)
    utl = sorted(r["util"] for r in out)
    print(f"\n  {len(out)} wallets simulated over {DAYS} days at {BANK:.0f} SOL")
    print(f"    follower return   median {100*rets[len(rets)//2]:+.1f}%   "
          f"p25 {100*rets[len(rets)//4]:+.1f}%   p75 {100*rets[3*len(rets)//4]:+.1f}%")
    print(f"    capital utilisation median {100*utl[len(utl)//2]:.0f}% "
          f"-- the number rule 14 was missing")
    conc = [r["top5"] for r in out if r["top5"] is not None]
    if conc:
        conc.sort()
        print(f"    share of follower P&L from its 5 best positions: "
              f"median {100*conc[len(conc)//2]:.0f}%")
    bad = [r for r in out if r["ret"] > r["target_ret"] * 3 + 0.05]
    if bad:
        print(f"    WARNING {len(bad)} wallets show the follower beating the target by >3x "
              f"-- inspect before quoting")

    # TAIL: with one bankroll you catch a SUBSET. Resample which positions land.
    import random
    print(f"\n  BOOTSTRAP over which positions a single follower actually catches")
    print(f"  {'wallet':<46}{'p10':>9}{'median':>9}{'p90':>9}{'P(loss)':>9}{'top5':>7}")
    for r in sorted(out, key=lambda z: -z["ret"])[:8]:
        pcs = r["taken_pcts"]
        if len(pcs) < 20: continue
        rnd = random.Random(31); draws = []
        k = max(1, r["taken"])
        for _ in range(3000):
            g = [pcs[rnd.randrange(len(pcs))] for _ in range(k)]
            draws.append(sum(sz * p * r["keep"] for sz, p in g) / BANK)
        draws.sort()
        pl = sum(1 for d in draws if d < 0) / len(draws)
        t5 = f"{100*r['top5']:.0f}%" if r["top5"] is not None else "n/a"
        print(f"  {r['w']:<46}{100*draws[300]:>+8.0f}%{100*draws[1500]:>+8.0f}%"
              f"{100*draws[2700]:>+8.0f}%{100*pl:>8.0f}%{t5:>7}")
print(f"\n  UPPER BOUND. No slippage, no rent, no missed fills, and it assumes the copier")
print(f"  reproduces the target's per-position outcome at their own size.")
