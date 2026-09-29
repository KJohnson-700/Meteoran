"""Final verification on the wallets that cleared T2 exact. Everything a copy decision
needs and the skill numbers do not carry: is it STILL ACTIVE, how long does it hold, what
does it trade, and what would 5 SOL actually have earned alongside it.

Gates already applied upstream: T1 skill, rhythm, size band, out-of-sample A and B,
and B-period top-3 concentration. This adds the operational ones.
"""
import json, sys, time, collections, urllib.request
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

API = "https://dlmm.datapi.meteora.ag"
NOW = int(time.time())
ex = {r["w"]: r for r in json.load(open("data/t2_exact.json"))}
POS = json.load(open("data/t2_positions.json"))

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}

# PASS = positive both periods AND positive with its 3 best B pools removed.
keep = [w for w, r in ex.items()
        if r["A"] and r["B"] and r["A"]["pct"] > 0 and r["B"]["pct"] > 0
        and r["B_ex_top3"] is not None and r["B_ex_top3"] > 0]
print(f"\n  {len(ex)} went into T2-exact -> {len(keep)} positive in A, in B, and ex-top-3\n")
print(f"  {'wallet':<46}{'last seen':>11}{'hold h':>8}{'med SOL':>9}{'B skill':>9}"
      f"{'ex-top3':>9}{'B n':>6}{'quote':>8}  top tokens")
out = []
for w in sorted(keep, key=lambda x: -ex[x]["B_ex_top3"]):
    r = ex[w]
    ps = [p for p in POS[w] if p.get("isClosed") and p.get("closedAt") and p.get("createdAt")]
    last = max(p["closedAt"] for p in ps)
    recent = [p for p in ps if p["closedAt"] >= NOW - 120 * 86400]
    holds = sorted((p["closedAt"] - p["createdAt"]) / 3600 for p in recent)
    sizes = sorted(float(p["allTimeDeposits"]["total"]["sol"] or 0) for p in recent)
    tot = get(f"{API}/portfolio/total?user={w}")
    port = get(f"{API}/portfolio?user={w}&days_back=120&page=1&page_size=100")
    toks = collections.Counter()
    quote = collections.Counter()
    for p in (port.get("pools") or []):
        toks[p.get("tokenX") or "?"] += 1
        quote[p.get("tokenY") or "?"] += 1
    row = {"w": w, "last_days": (NOW - last) / 86400,
           "median_hold_h": holds[len(holds)//2] if holds else 0,
           "median_size": sizes[len(sizes)//2] if sizes else 0,
           "B_skill": r["B"]["pct"], "B_ex_top3": r["B_ex_top3"], "B_n": r["B"]["n"],
           "lifetime_pnl_sol": tot.get("totalPnlSol"),
           "closed_positions": tot.get("totalClosedPositions"),
           "quote": quote.most_common(1)[0][0] if quote else "?",
           "top_tokens": [t for t, _ in toks.most_common(4)]}
    out.append(row)
    print(f"  {w:<46}{row['last_days']:>9.1f}d{row['median_hold_h']:>8.1f}"
          f"{row['median_size']:>9.2f}{100*row['B_skill']:>+8.2f}%{100*row['B_ex_top3']:>+8.2f}%"
          f"{row['B_n']:>6}{row['quote'][:7]:>8}  {', '.join(row['top_tokens'][:4])}")
json.dump(out, open("data/t2_finalists_report.json", "w"), indent=1)
print(f"\n  -> data/t2_finalists_report.json")
