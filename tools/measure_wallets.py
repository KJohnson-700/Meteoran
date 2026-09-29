"""Full measurement stack for an ad-hoc wallet list (e.g. harvested from a pool scan).

Reads addresses from argv or stdin, dedupes, and reports the only three things that
matter for this project:
  LP skill   bounded vs-HODL (T1)   -- not raw P&L, which is uncorrelated (rule 9)
  rhythm     sleep6h / per_day / off_days (rule 5) -- operator wants humans, not bots
  size       avg SOL per position -- the $500 bankroll makes this a hard gate (rule 10)
"""
import json, sys, re, time, collections, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

API = "https://dlmm.datapi.meteora.ag"
raw = " ".join(sys.argv[1:]) or sys.stdin.read()
ws = list(dict.fromkeys(re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", raw)))
print(f"  {len(ws)} unique addresses\n")

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0",
                                           "Accept": "application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(.3 * (a + 1))
    return {}

def pull(w):
    out = []
    for pg in range(1, 11):
        d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
        out += d.get("pools") or []
        if not d.get("hasNext"): break
    return out

def measure(w):
    ps = pull(w)
    if not ps: return {"w": w, "err": "no data"}
    dep = sk = fees = pnl = 0.0; used = beat = 0; udep = upnl = 0.0; per = []
    for p in ps:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        pnl += f(p, "pnlSol"); fees += f(p, "totalFeeSol")
        r = vs_hodl(p)
        if r is None: udep += d0; upnl += f(p, "pnlSol"); continue
        dep += d0; sk += r[0]; used += 1; beat += r[0] > 0; per.append(r[0])
    if used < 3 or dep <= 0: return {"w": w, "err": f"only {used} usable pools"}
    o = {"w": w, "pools": used, "pnl": pnl, "fees": fees, "dep": dep,
         "skill": 100 * (sk + upnl) / (dep + udep), "beat": 100 * beat / used,
         "avg": dep / used}
    # CONCENTRATION: skill from a handful of pools is one token's story, not an edge.
    pos = sorted([x for x in per if x > 0], reverse=True)
    tot = sum(per)
    o["top1"] = 100 * pos[0] / tot if pos and tot > 0 else 0
    o["top3"] = 100 * sum(pos[:3]) / tot if pos and tot > 0 else 0
    ts = [int(p["lastClosedAt"]) for p in ps if p.get("lastClosedAt")]
    if len(ts) >= 25:
        hrs = collections.Counter(time.gmtime(t).tm_hour for t in ts)
        best = min(sum(hrs[(h + i) % 24] for i in range(6)) for h in range(24))
        days = collections.Counter(time.strftime("%Y-%m-%d", time.gmtime(t)) for t in ts)
        span = (max(ts) - min(ts)) / 86400.0
        o.update(sleep=100 * best / len(ts), per_day=len(ts) / max(1, len(days)),
                 off=100 * (1 - len(days) / max(1, span)))
    return o

with ThreadPoolExecutor(max_workers=8) as ex: res = list(ex.map(measure, ws))
res.sort(key=lambda x: -x.get("skill", -1e9))
print(f"  {'wallet':<46}{'skill':>8}{'beat':>6}{'pools':>7}{'avgPos':>8}"
      f"{'lifePnL':>9}{'top3':>6}{'/day':>6}{'sleep':>7}{'off':>6}  verdict")
for r in res:
    if r.get("err"): print(f"  {r['w']:<46}{r['err']:>8}"); continue
    v = []
    if r["avg"] > 10: v.append("TOO BIG")
    if "sleep" in r:
        if r["sleep"] >= 12 or r["per_day"] >= 40: v.append("BOT-LIKE")
    else: v.append("no rhythm(<25 closes)")
    if r["skill"] <= 0: v.append("no edge")
    if r["pools"] < 25: v.append("thin sample")
    if r.get("top3", 0) > 65: v.append(f"CONCENTRATED(top3={r['top3']:.0f}%)")
    print(f"  {r['w']:<46}{r['skill']:>+7.2f}%{r['beat']:>5.0f}%{r['pools']:>7}"
          f"{r['avg']:>8.2f}{r['pnl']:>+9.1f}{r.get('top3',0):>5.0f}%"
          f"{r.get('per_day',0):>6.1f}{r.get('sleep',0):>6.1f}%{r.get('off',0):>5.0f}%"
          f"  {', '.join(v) if v else 'PASSES ALL'}")
# ACCUMULATE, never overwrite -- these come in one paste at a time and the earlier
# batches are the record of what has already been rejected.
import os
prev = json.load(open("data/scanned_wallets.json")) if os.path.exists("data/scanned_wallets.json") else []
merged = {x["w"]: x for x in prev}
merged.update({x["w"]: x for x in res})
json.dump(list(merged.values()), open("data/scanned_wallets.json", "w"), indent=1)
print(f"\n  {len(res)} measured this run, {len(merged)} total -> data/scanned_wallets.json")
