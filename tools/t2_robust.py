"""T2 robustness -- does the out-of-sample result survive being attacked?

t2_oos.py gave Spearman(A skill, B skill) = +0.38 at one cut date. Four ways that could
be an artifact rather than skill persistence, each tested here:

  1 CUT DATE       a single cut could be a lucky slice. Sweep it.
  2 SIGNIFICANCE   +0.38 needs a null built from THIS data, not a textbook formula --
                   wallets share market conditions, so they are not independent draws.
                   Permutation (shuffle B against A) + bootstrap over wallets.
  3 THE BOUND      uncovered rows are charged their full loss in BOTH periods, so a
                   wallet that habitually leaves uncovered rows correlates with itself
                   for a reason that is not skill. Recompute on covered rows only.
  4 SIZE           the whole project is a 5 SOL bankroll. A result that only holds for
                   whales is not actionable. Re-test inside the 0.5-10 SOL band.
"""
import json, sys, time, random, statistics as st
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl
from t2_oos import spearman

MIN_SIDE = 8
CACHE = json.load(open("data/t2_pools.json"))


def measure(pools, covered_only=False):
    dep = sk = udep = upnl = 0.0
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
    if covered_only:
        return {"n": n, "dep": dep, "skill": sk, "pct": sk / dep,
                "beat": beat / n, "raw": raw, "avg": dep / n}
    return {"n": n, "dep": dep + udep, "skill": sk + upnl,
            "pct": (sk + upnl) / (dep + udep), "beat": beat / n, "raw": raw,
            "avg": (dep + udep) / (n + unc)}


def split(cut_days, covered_only=False):
    cut = int(time.time()) - cut_days * 86400
    out = []
    for rec in CACHE:
        A = measure([p for p in rec["pools"] if p["t"] < cut], covered_only)
        B = measure([p for p in rec["pools"] if p["t"] >= cut], covered_only)
        if A and B: out.append({"w": rec["w"], "A": A, "B": B})
    return out


def rho_ci(rows, reps=1000, seed=3):
    """Bootstrap over WALLETS, and a permutation null at the same n."""
    rnd = random.Random(seed)
    A = [r["A"]["pct"] for r in rows]; B = [r["B"]["pct"] for r in rows]
    bs = []
    for _ in range(reps):
        idx = [rnd.randrange(len(rows)) for _ in range(len(rows))]
        bs.append(spearman([A[i] for i in idx], [B[i] for i in idx]))
    bs.sort()
    perm = []
    for _ in range(reps):
        sh = B[:]; rnd.shuffle(sh)
        perm.append(spearman(A, sh))
    obs = spearman(A, B)
    beat = sum(1 for p in perm if p >= obs)
    perm.sort()
    return obs, bs[int(.025 * reps)], bs[int(.975 * reps)], perm[int(.975 * reps)], (beat + 1) / (reps + 1)


print("\n  1 CUT-DATE SWEEP  (bounded skill, min 8 pools/side)")
print(f"    {'cut':>6}{'date':>13}{'n':>7}{'rho(skill)':>12}{'rho(rawpnl)':>13}"
      f"{'A pooled':>11}{'B pooled':>11}")
for cd in (60, 90, 120, 150, 180, 240):
    rows = split(cd)
    if len(rows) < 50:
        print(f"    {cd:>4}d  too few wallets span the cut ({len(rows)})"); continue
    dA = sum(r["A"]["dep"] for r in rows); dB = sum(r["B"]["dep"] for r in rows)
    print(f"    {cd:>5}d{time.strftime('%Y-%m-%d', time.gmtime(time.time()-cd*86400)):>13}"
          f"{len(rows):>7}"
          f"{spearman([r['A']['pct'] for r in rows], [r['B']['pct'] for r in rows]):>+12.4f}"
          f"{spearman([r['A']['raw'] for r in rows], [r['B']['pct'] for r in rows]):>+13.4f}"
          f"{100*sum(r['A']['skill'] for r in rows)/dA:>+10.3f}%"
          f"{100*sum(r['B']['skill'] for r in rows)/dB:>+10.3f}%")

rows = split(120)
print("\n  2 SIGNIFICANCE at the 120d cut")
obs, lo, hi, p95, pval = rho_ci(rows)
print(f"    observed rho            {obs:+.4f}")
print(f"    bootstrap 95% CI        [{lo:+.4f}, {hi:+.4f}]   (resampling wallets)")
print(f"    permutation null p95    {p95:+.4f}   p-value {pval:.4f}")
print(f"    -> {'SURVIVES' if lo > 0 and pval < 0.05 else 'DOES NOT SURVIVE'}")

print("\n  3 THE BOUND  -- uncovered rows charged in both periods could self-correlate")
cov = split(120, covered_only=True)
print(f"    bounded    n {len(rows):>4}  rho "
      f"{spearman([r['A']['pct'] for r in rows], [r['B']['pct'] for r in rows]):+.4f}")
print(f"    covered    n {len(cov):>4}  rho "
      f"{spearman([r['A']['pct'] for r in cov], [r['B']['pct'] for r in cov]):+.4f}")

print("\n  4 SIZE BAND  -- the bankroll is ~5 SOL, so only this cohort is actionable")
print(f"    {'band (avg SOL/pool in A)':<28}{'n':>6}{'rho':>10}{'B pooled':>11}{'B median':>11}")
for lo_b, hi_b, lab in ((0, 0.5, "under 0.5"), (0.5, 10, "0.5 - 10  <- his size"),
                        (10, 100, "10 - 100"), (100, 1e9, "over 100")):
    sub = [r for r in rows if lo_b <= r["A"]["avg"] < hi_b]
    if len(sub) < 20:
        print(f"    {lab:<28}{len(sub):>6}   too few"); continue
    d = sum(r["B"]["dep"] for r in sub)
    print(f"    {lab:<28}{len(sub):>6}"
          f"{spearman([r['A']['pct'] for r in sub], [r['B']['pct'] for r in sub]):>+10.4f}"
          f"{100*sum(r['B']['skill'] for r in sub)/d:>+10.3f}%"
          f"{100*st.median(r['B']['pct'] for r in sub):>+10.2f}%")
