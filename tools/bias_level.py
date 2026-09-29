"""Rule 11, the open problem: 84-88% of measured wallets show POSITIVE vs-HODL. That is
high enough to suspect our own method rather than a real edge. T2 validated the RANKING
(a common bias cancels in a rank); the LEVEL is what an allocation gets sized against,
so it has to be attacked separately.

Three candidate mechanisms, each testable on its own:

  1 WALLET SURVIVORSHIP  a wallet that blows up stops trading, so it never spans the
                         periods we measure. Compare period-A skill of wallets that
                         KEPT trading into C against those that vanished. Free -- it is
                         all in data/t2_pools.json already.
  2 POSITION CENSORING   losers do not get closed, they get held. Every realised number
                         we have is therefore conditioned on the LP choosing to exit.
                         Compare the open book against the same wallets' closed history.
  3 NOT A BIAS AT ALL    an LP in a 1-2% fee pool earns fees continuously and loses to
                         IL in a fat left tail. "Usually a small win, occasionally a big
                         loss" IS the genuine LP payoff, and it produces a high positive
                         rate with a much lower mean. Test the SHAPE of the distribution.
"""
import json, sys, time, statistics as st, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

NOW = int(time.time())
A0, A1 = NOW - 365 * 86400, NOW - 240 * 86400
C0 = NOW - 120 * 86400
API = "https://dlmm.datapi.meteora.ag"
CACHE = json.load(open("data/t2_pools.json"))


def measure(pools, minn=6):
    dep = sk = udep = upnl = 0.0; n = beat = 0
    for p in pools:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None: udep += d0; upnl += f(p, "pnlSol"); continue
        v, _h, _ = r
        dep += d0; sk += v; n += 1; beat += v > 0
    if n < minn or dep <= 0: return None
    return {"n": n, "dep": dep + udep, "skill": sk + upnl,
            "pct": (sk + upnl) / (dep + udep), "beat": beat / n}


# ---------------------------------------------------------------- 1 survivorship
print("\n  1 WALLET SURVIVORSHIP — does quitting correlate with being bad?")
alive, gone = [], []
for rec in CACHE:
    A = measure([p for p in rec["pools"] if A0 <= p["t"] < A1])
    if not A: continue
    (alive if any(p["t"] >= C0 for p in rec["pools"]) else gone).append(A)
print(f"    active in period A: {len(alive)+len(gone):,}  "
      f"-> still trading in C: {len(alive):,}   stopped: {len(gone):,} "
      f"({100*len(gone)/max(len(alive)+len(gone),1):.0f}%)")
print(f"    {'group':<26}{'n':>7}{'A capital':>13}{'A pooled':>11}{'A median':>11}{'A>0':>7}")
for lab, g in (("kept trading into C", alive), ("stopped before C", gone)):
    if not g: continue
    d = sum(r["dep"] for r in g)
    print(f"    {lab:<26}{len(g):>7}{d:>13,.0f}{100*sum(r['skill'] for r in g)/d:>+10.3f}%"
          f"{100*st.median(r['pct'] for r in g):>+10.2f}%"
          f"{100*sum(1 for r in g if r['pct']>0)/len(g):>6.0f}%")
if alive and gone:
    gap = st.median(r["pct"] for r in alive) - st.median(r["pct"] for r in gone)
    print(f"    survivor premium (median)  {100*gap:+.3f} pp"
          f"   <- how much conditioning on survival inflates the level")

# ---------------------------------------------------------------- 3 shape
print("\n  3 DISTRIBUTION SHAPE — is a high positive rate even anomalous for an LP?")
per = []
for rec in CACHE:
    for p in rec["pools"]:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None: continue
        per.append((r[0] / d0, d0))
per.sort()
v = [x for x, _ in per]; n = len(v)
tot_d = sum(d for _, d in per)
print(f"    {n:,} pool-level vs-HODL observations, {tot_d:,.0f} SOL")
print(f"    positive        {100*sum(1 for x in v if x>0)/n:.1f}%")
print(f"    median          {100*v[n//2]:+.2f}%")
print(f"    unweighted mean {100*sum(v)/n:+.2f}%")
print(f"    CAPITAL-WEIGHTED mean {100*sum(x*d for x,d in per)/tot_d:+.3f}%   <- the only one that pays")
print(f"    p1 {100*v[n//100]:+.1f}%   p5 {100*v[n//20]:+.1f}%   p25 {100*v[n//4]:+.2f}%"
      f"   p75 {100*v[3*n//4]:+.2f}%   p95 {100*v[19*n//20]:+.1f}%   p99 {100*v[99*n//100]:+.1f}%")
neg = [x for x in v if x < 0]; pos = [x for x in v if x > 0]
print(f"    mean WIN  {100*sum(pos)/len(pos):+.2f}%  over {len(pos):,}")
print(f"    mean LOSS {100*sum(neg)/len(neg):+.2f}%  over {len(neg):,}")
print(f"    -> a {100*len(pos)/n:.0f}% win rate paired with losses "
      f"{abs(sum(neg)/len(neg))/(sum(pos)/len(pos)):.1f}x the size of wins")
worst = sum(x*d for x, d in per if x < 0)
print(f"    total lost in the left tail {worst:,.0f} SOL vs "
      f"{sum(x*d for x,d in per if x>0):,.0f} SOL won")

# ---------------------------------------------------------------- 2a the truncated tail
print("\n  2a UNCOVERED ROWS — the left tail we cannot price, measured at full scale")
cov_d = cov_s = unc_d = unc_p = 0.0
cov_n = unc_n = 0
unc_pct = []
for rec in CACHE:
    for p in rec["pools"]:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None:
            unc_n += 1; unc_d += d0; pl = f(p, "pnlSol"); unc_p += pl
            unc_pct.append(pl / d0)
        else:
            cov_n += 1; cov_d += d0; cov_s += r[0]
unc_pct.sort(); m = len(unc_pct)
print(f"    covered    {cov_n:>9,} rows  {cov_d:>13,.0f} SOL   skill {100*cov_s/cov_d:+.3f}%")
print(f"    UNCOVERED  {unc_n:>9,} rows  {unc_d:>13,.0f} SOL "
      f"({100*unc_d/(cov_d+unc_d):.1f}% of capital)   realised {100*unc_p/unc_d:+.2f}%")
if m:
    print(f"    uncovered realised pct:  median {100*unc_pct[m//2]:+.2f}%   "
          f"p10 {100*unc_pct[m//10]:+.1f}%   p90 {100*unc_pct[9*m//10]:+.1f}%   "
          f"share losing {100*sum(1 for x in unc_pct if x<0)/m:.0f}%")
print(f"    capital-weighted skill, covered only        {100*cov_s/cov_d:+.3f}%")
print(f"    same, BOUNDED (uncovered charged full loss) {100*(cov_s+unc_p)/(cov_d+unc_d):+.3f}%")
print(f"    the bound costs {100*(cov_s/cov_d - (cov_s+unc_p)/(cov_d+unc_d)):.3f} pp"
      f"  <- the entire truncation effect, if the bound is right")

# ---------------------------------------------------------------- 2b position censoring
print("\n  2b POSITION CENSORING — do losers simply never get closed?")
print("     Every realised number we have is conditioned on the LP CHOOSING to exit.")
print("     If underwater positions are held open instead, they never enter the sample.")
import os
if not os.path.exists("data/t2_positions.json"):
    print("     no position cache -- run tools/t2_exact.py first")
else:
    POS = json.load(open("data/t2_positions.json"))
    print(f"\n     {'wallet':<14}{'open':>6}{'closed':>8}{'open cap':>11}{'cap %':>8}"
          f"{'open m2m':>11}{'closed real':>13}{'open age d':>12}{'closed age d':>13}")
    tot_o = tot_oc = tot_c = tot_cc = 0.0
    for w, ps in POS.items():
        op = [p for p in ps if not p.get("isClosed")]
        cl = [p for p in ps if p.get("isClosed")]
        oc = sum(float(p["allTimeDeposits"]["total"]["sol"] or 0) for p in op)
        cc = sum(float(p["allTimeDeposits"]["total"]["sol"] or 0) for p in cl)
        if cc <= 0: continue
        op_p = sum(float(p.get("pnlSol") or 0) for p in op)
        cl_p = sum(float(p.get("pnlSol") or 0) for p in cl)
        oa = sorted((NOW - p["createdAt"]) / 86400 for p in op if p.get("createdAt"))
        ca = sorted((NOW - p["createdAt"]) / 86400 for p in cl if p.get("createdAt"))
        tot_o += op_p; tot_oc += oc; tot_c += cl_p; tot_cc += cc
        print(f"     {w[:12]:<14}{len(op):>6}{len(cl):>8}{oc:>11.1f}"
              f"{100*oc/(oc+cc):>7.1f}%{(100*op_p/oc if oc else 0):>+10.2f}%"
              f"{100*cl_p/cc:>+12.2f}%{(oa[len(oa)//2] if oa else 0):>12.1f}"
              f"{(ca[len(ca)//2] if ca else 0):>13.1f}")
    print(f"\n     POOLED   open book {tot_oc:,.0f} SOL "
          f"({100*tot_oc/(tot_oc+tot_cc):.1f}% of deployed capital)"
          f"   mark-to-market {100*tot_o/tot_oc:+.2f}%")
    print(f"              closed     {tot_cc:,.0f} SOL   realised {100*tot_c/tot_cc:+.2f}%")
    drag = (tot_o + tot_c) / (tot_oc + tot_cc) - tot_c / tot_cc
    print(f"     including the open book at market moves realised P&L by {100*drag:+.3f} pp")
