"""T2-ABC -- test the SELECTION PROCEDURE, not the wallets.

t2_oos.py proved that A-skill ranks B-skill (rho +0.38). But the shortlist was then
picked with a rule that READS period B ("positive in A and in B"), so those wallets'
B numbers are selected-on and cannot be quoted as a forecast. That is the same
circularity rule 8 warns about, one level up.

So: three periods. Run the ENTIRE live selection rule using only A and B, then score the
wallets it picks on C, which the rule never touched.

    A  [365d, cut1)   B  [cut1, cut2)   C  [cut2, now)

The benchmark is not zero -- 84.6% of measured wallets show positive vs-HODL (rule 11,
unresolved), so a positive C means nothing on its own. The bar is the C skill of every
wallet that spanned the same periods and was NOT selected.
"""
import json, sys, time, random, statistics as st
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

CUT1_D = int(sys.argv[1]) if len(sys.argv) > 1 else 240
CUT2_D = int(sys.argv[2]) if len(sys.argv) > 2 else 120
MIN_SIDE = int(sys.argv[3]) if len(sys.argv) > 3 else 6
NOW = int(time.time())
C1, C2 = NOW - CUT1_D * 86400, NOW - CUT2_D * 86400

CACHE = json.load(open("data/t2_pools.json"))
lb = {r["w"]: r for r in json.load(open("data/skill_leaderboard.json"))}
for r in json.load(open("data/scanned_wallets.json")):
    lb.setdefault(r["w"], {"pools": r["pools"], "sleep": r["sleep"] / 100,
                           "per_day": r["per_day"]})


def measure(pools):
    dep = sk = udep = upnl = 0.0; n = beat = unc = 0
    for p in pools:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None:
            unc += 1; udep += d0; upnl += f(p, "pnlSol"); continue
        v, _h, _ = r
        dep += d0; sk += v; n += 1; beat += v > 0
    if n < MIN_SIDE or dep <= 0: return None
    return {"n": n, "dep": dep + udep, "skill": sk + upnl,
            "pct": (sk + upnl) / (dep + udep), "beat": beat / n,
            "avg": (dep + udep) / (n + unc)}


rows = []
for rec in CACHE:
    A = measure([p for p in rec["pools"] if p["t"] < C1])
    B = measure([p for p in rec["pools"] if C1 <= p["t"] < C2])
    C = measure([p for p in rec["pools"] if p["t"] >= C2])
    if A and B and C: rows.append({"w": rec["w"], "A": A, "B": B, "C": C})

print(f"\n  T2-ABC   A[365d,{CUT1_D}d)  B[{CUT1_D}d,{CUT2_D}d)  C[{CUT2_D}d,now)"
      f"   min {MIN_SIDE} pools per period")
print(f"  {len(CACHE):,} cached -> {len(rows):,} wallets active in ALL THREE periods")
if len(rows) < 40:
    print("  too few wallets span three periods -- widen the cuts or lower MIN_SIDE"); sys.exit()


def pooled(g, k="C"):
    d = sum(r[k]["dep"] for r in g)
    return sum(r[k]["skill"] for r in g) / d if d else 0.0


def rule(r):
    """The live selection rule from t2_survivors.py, reading ONLY A and B."""
    L = lb.get(r["w"], {})
    return (r["A"]["pct"] > 0 and r["B"]["pct"] > 0
            and 0.5 <= r["B"]["avg"] <= 10
            and "sleep" in L and L["sleep"] < 0.12 and L["per_day"] < 40
            and L.get("pools", 0) >= 30)


sel = [r for r in rows if rule(r)]
rest = [r for r in rows if not rule(r)]
print(f"\n  the rule picks {len(sel)} of {len(rows)}; {len(rest)} are the control group\n")
print(f"  {'group':<34}{'n':>6}{'C capital':>13}{'C pooled':>11}{'C median':>11}"
      f"{'C beat':>9}{'C>0':>7}")
for lab, g in (("SELECTED by the rule (A+B only)", sel), ("everyone else", rest),
               ("all wallets spanning A,B,C", rows)):
    if not g: continue
    print(f"  {lab:<34}{len(g):>6}{sum(r['C']['dep'] for r in g):>13,.0f}"
          f"{100*pooled(g):>+10.3f}%{100*st.median(r['C']['pct'] for r in g):>+10.2f}%"
          f"{100*st.mean(r['C']['beat'] for r in g):>8.0f}%"
          f"{100*sum(1 for r in g if r['C']['pct'] > 0)/len(g):>6.0f}%")

# Is the gap bigger than picking the same number of wallets at random?
rnd = random.Random(5)
obs = st.median(r["C"]["pct"] for r in sel) - st.median(r["C"]["pct"] for r in rows)
null = []
for _ in range(5000):
    g = rnd.sample(rows, len(sel))
    null.append(st.median(r["C"]["pct"] for r in g) - st.median(r["C"]["pct"] for r in rows))
null.sort()
p = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
print(f"\n  median C uplift vs the whole field   {100*obs:+.3f} pp")
print(f"  random-{len(sel)} null, 95th pct        {100*null[int(.95*len(null))]:+.3f} pp"
      f"   p = {p:.4f}")
print(f"  -> the SELECTION RULE {'GENERALISES' if p < 0.05 else 'IS NOT DISTINGUISHABLE FROM CHANCE'}")

json.dump({"cut1_d": CUT1_D, "cut2_d": CUT2_D, "n_all": len(rows), "n_sel": len(sel),
           "C_pooled_sel": pooled(sel), "C_pooled_rest": pooled(rest),
           "C_median_sel": st.median(r["C"]["pct"] for r in sel),
           "C_median_all": st.median(r["C"]["pct"] for r in rows),
           "uplift_pp": obs, "p": p,
           "selected": [r["w"] for r in sel]},
          open("data/t2_abc.json", "w"), indent=1)
print(f"\n  -> data/t2_abc.json")
