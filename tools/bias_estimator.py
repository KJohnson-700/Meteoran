"""Is the vs-HODL exit-price ESTIMATOR itself biased?

vs_hodl() prices a token's exit as totalWithdrawalTokenTSol / totalWithdrawalTokenT --
a value-weighted average over ALL withdrawal events. That is EXACT for a position with
one add and one remove, and an approximation otherwise. If the approximation is biased,
every level we quote inherits it, and no amount of out-of-sample testing would catch it
because T2 only validates the ranking.

So: sample closed positions, count their add/remove events via
/positions/{addr}/historical, and compare the vs-HODL level on positions where the
estimator is EXACT against those where it is approximate. Same population, same pools,
only the estimator's accuracy differs.
"""
import json, sys, time, random, statistics as st, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

def flat(pos):
    """Position JSON -> the flat shape vs_hodl() reads. Duplicated from t2_exact on
    purpose: importing that module runs it."""
    d, wd, fe = pos["allTimeDeposits"], pos["allTimeWithdrawals"], pos["allTimeFees"]
    o = {"totalDepositSol": d["total"]["sol"], "totalWithdrawalSol": wd["total"]["sol"],
         "totalFeeSol": fe["total"]["sol"], "pnlSol": pos.get("pnlSol")}
    for T, k in (("TokenX", "tokenX"), ("TokenY", "tokenY")):
        o[f"totalDeposit{T}"] = d[k]["amount"];     o[f"totalDeposit{T}Sol"] = d[k]["amountSol"]
        o[f"totalWithdrawal{T}"] = wd[k]["amount"]; o[f"totalWithdrawal{T}Sol"] = wd[k]["amountSol"]
    return o


API = "https://dlmm.datapi.meteora.ag"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 500

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}

POS = json.load(open("data/t2_positions.json"))
pool = [(w, p) for w, ps in POS.items() for p in ps
        if p.get("isClosed") and float(p["allTimeDeposits"]["total"]["sol"] or 0) > 0]
rnd = random.Random(17)
samp = rnd.sample(pool, min(N, len(pool)))
print(f"  sampling {len(samp)} closed positions from {len(pool):,} across {len(POS)} wallets\n")

def one(x):
    w, p = x
    ev = (get(f"{API}/positions/{p['positionAddress']}/historical") or {}).get("events") or []
    if not ev: return None
    na = sum(1 for e in ev if e.get("eventType") == "add")
    nr = sum(1 for e in ev if e.get("eventType") == "remove")
    fl = flat(p)
    r = vs_hodl(fl)
    d0 = f(fl, "totalDepositSol")
    return {"adds": na, "removes": nr, "dep": d0,
            "vs": (r[0] / d0) if (r and d0 > 0) else None,
            "covered": r is not None}

t0 = time.time(); res = []
with ThreadPoolExecutor(max_workers=24) as ex:
    for i, r in enumerate(ex.map(one, samp), 1):
        if r: res.append(r)
        if i % 50 == 0:
            print(f"    {i}/{len(samp)}  {i/(time.time()-t0):.1f}/s", flush=True)
print(f"  {len(res)} positions with event history\n")

def summarise(lab, g):
    cov = [r for r in g if r["covered"] and r["vs"] is not None]
    if len(cov) < 10:
        print(f"  {lab:<34}{len(g):>6}   too few covered"); return
    d = sum(r["dep"] for r in cov)
    wt = sum(r["vs"] * r["dep"] for r in cov) / d
    v = sorted(r["vs"] for r in cov)
    print(f"  {lab:<34}{len(g):>6}{100*len(cov)/len(g):>8.0f}%{d:>11,.0f}"
          f"{100*wt:>+12.3f}%{100*v[len(v)//2]:>+11.2f}%"
          f"{100*sum(1 for x in v if x>0)/len(v):>8.0f}%")

print(f"  {'group':<34}{'n':>6}{'covered':>8}{'SOL':>11}{'cap-wtd vs-HODL':>13}"
      f"{'median':>11}{'>0':>8}")
exact = [r for r in res if r["adds"] == 1 and r["removes"] == 1]
multi = [r for r in res if r["adds"] > 1 or r["removes"] > 1]
summarise("EXACT (1 add, 1 remove)", exact)
summarise("approximate (multi-event)", multi)
summarise("  of which multi-ADD", [r for r in res if r["adds"] > 1])
summarise("  of which multi-REMOVE", [r for r in res if r["removes"] > 1])
summarise("ALL", res)

ce = [r["vs"] for r in exact if r["covered"] and r["vs"] is not None]
cm = [r["vs"] for r in multi if r["covered"] and r["vs"] is not None]
if len(ce) >= 10 and len(cm) >= 10:
    obs = st.median(ce) - st.median(cm)
    both = ce + cm
    rnd2 = random.Random(23); null = []
    for _ in range(4000):
        rnd2.shuffle(both)
        null.append(st.median(both[:len(ce)]) - st.median(both[len(ce):]))
    null.sort()
    p = (sum(1 for x in null if abs(x) >= abs(obs)) + 1) / (len(null) + 1)
    print(f"\n  median gap EXACT - approximate  {100*obs:+.3f} pp   permutation p = {p:.3f}")
    print(f"  -> the estimator "
          f"{'IS biased between the two groups' if p < 0.05 else 'shows NO detectable bias'}")
print(f"\n  event-count mix: "
      f"{100*len(exact)/len(res):.0f}% exact, {100*len(multi)/len(res):.0f}% approximate")
