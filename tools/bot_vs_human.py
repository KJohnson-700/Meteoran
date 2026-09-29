"""Separate human LPs from bots on activity RHYTHM, not on P&L.

A bot closes positions around the clock at a steady rate. A human sleeps, takes days
off, and works in sessions -- the pattern the operator described: ~15 positions opened
together, closed 15-24h later, about an hour a day.

Three signals, all from `lastClosedAt`:
  sleep_gap   the quietest 6 consecutive UTC hours as a share of total closes. A 24/7
              bot sits near 25% (6/24); a human with a sleep cycle drops well below.
  per_day     closes per ACTIVE day. The operator's own description is ~15/day.
  off_days    share of days in the span with no activity at all.
"""
import json, subprocess, collections, time
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0"
API = "https://dlmm.datapi.meteora.ag"


def pools(w, pages=4):
    out = []
    for pg in range(1, pages + 1):
        p = subprocess.run(["curl", "-s", "-m", "25", "-A", UA,
                            f"{API}/portfolio?user={w}&days_back=90&page=%d&page_size=100" % pg],
                           capture_output=True, text=True)
        try:
            d = json.loads(p.stdout)
        except Exception:
            break
        out += d.get("pools") or []
        if not d.get("hasNext"):
            break
    return out


def profile(rec):
    w = rec["w"]
    ps = pools(w)
    ts = [int(p["lastClosedAt"]) for p in ps if p.get("lastClosedAt")]
    if len(ts) < 25:
        return None
    hours = collections.Counter(time.gmtime(t).tm_hour for t in ts)
    best = min(sum(hours[(h + i) % 24] for i in range(6)) for h in range(24))
    days = collections.Counter(time.strftime("%Y-%m-%d", time.gmtime(t)) for t in ts)
    span = (max(ts) - min(ts)) / 86400.0
    return {**rec, "n": len(ts), "sleep": best / len(ts),
            "per_day": len(ts) / max(1, len(days)),
            "active_days": len(days), "span": span,
            "off": 1 - len(days) / max(1, span)}


cands = [r for r in json.load(open("dlmm_pnl.json"))
         if r["closed"] >= 50 and abs(r["pnl_sol"]) < 50_000
         and -1.0 < r["pct_sol"] < 10 and r["pnl_sol"] * r["pnl_usd"] >= 0
         and r["pnl_sol"] > 0]
print(f"  profiling {len(cands)} profitable, sanity-checked wallets\n")
with ThreadPoolExecutor(max_workers=12) as ex:
    res = [r for r in ex.map(profile, cands) if r]
json.dump(res, open("human_profile.json", "w"))
print(f"  {len(res)} had >=25 dated closes\n")
hum = [r for r in res if r["sleep"] < 0.12 and r["per_day"] < 40]
print(f"  {'wallet':<46}{'closes':>7}{'/day':>7}{'sleep6h':>9}{'off-days':>9}{'SOL':>9}")
for r in sorted(hum, key=lambda x: -x["pnl_sol"])[:12]:
    print(f"  {r['w']:<46}{r['n']:>7}{r['per_day']:>7.1f}{100*r['sleep']:>8.1f}%"
          f"{100*r['off']:>8.0f}%{r['pnl_sol']:>+9.1f}")
print(f"\n  HUMAN-LIKE (sleep gap <12%, <40 closes/day): {len(hum)} of {len(res)}")
bots = [r for r in res if r["sleep"] >= 0.12 or r["per_day"] >= 40]
print(f"  BOT-LIKE: {len(bots)}")
