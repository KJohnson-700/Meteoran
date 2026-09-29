"""Pick the wallets that passed T2 *and* are actually copyable at a 5 SOL bankroll.

Gates, in the order they cost us something to learn:
  both periods    >=8 usable pools each side of the cut (t2_oos)
  HELD UP         positive vs-HODL skill in A AND in B -- this is the T2 gate itself
  size            0.5-10 SOL average position (rule 10: the old shortlist was 329-743)
  rhythm          sleep6h <12%, per_day <40 (rule 5, the operator's constraint)
  sample          >=30 pools lifetime (rule 13: prefer sample size over headline)
Concentration (rule 13) is checked afterwards by measure_wallets.py, which needs the
per-pool skill vector this script does not keep.
"""
import json, sys, time
sys.path.insert(0, "tools")
from t2_robust import split

CUT_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
rows = {r["w"]: r for r in split(CUT_DAYS)}
lb = {r["w"]: r for r in json.load(open("data/skill_leaderboard.json"))}
# Pool-scanned wallets carry the same metrics under measure_wallets.py's schema, where
# the rates are PERCENTS not fractions. Without this they have no rhythm field and get
# silently skipped -- which reads as "failed T2" when they were never tested.
for r in json.load(open("data/scanned_wallets.json")):
    lb.setdefault(r["w"], {"pools": r["pools"], "skill_pct_bounded": r["skill"] / 100,
                           "beat_rate": r["beat"] / 100, "sleep": r["sleep"] / 100,
                           "per_day": r["per_day"], "off": r["off"] / 100,
                           "raw_pnl": r["pnl"]})

out = []
for w, r in rows.items():
    L = lb.get(w, {})
    if not (r["A"]["pct"] > 0 and r["B"]["pct"] > 0): continue
    if not (0.5 <= r["A"]["avg"] <= 10): continue
    if "sleep" not in L: continue                      # <25 dated closes, rhythm unknown
    if L["sleep"] >= 0.12 or L["per_day"] >= 40: continue
    if L.get("pools", 0) < 30: continue
    out.append({"w": w, "A": r["A"]["pct"], "B": r["B"]["pct"],
                "nA": r["A"]["n"], "nB": r["B"]["n"], "avg": r["A"]["avg"],
                "pools": L["pools"], "life_skill": L["skill_pct_bounded"],
                "beat": L["beat_rate"], "sleep": L["sleep"], "per_day": L["per_day"],
                "off": L.get("off", 0), "raw": L["raw_pnl"]})
out.sort(key=lambda r: -min(r["A"], r["B"]))           # rank on the WEAKER period

print(f"\n  T2 SURVIVORS  cut {CUT_DAYS}d   {len(rows)} spanned both periods -> {len(out)} passed\n")
print(f"  {'wallet':<46}{'A skill':>9}{'B skill':>9}{'nA':>5}{'nB':>5}"
      f"{'pools':>7}{'life':>8}{'beat':>6}{'SOL/pos':>9}{'/day':>6}{'sleep':>7}{'off':>6}")
for r in out[:30]:
    print(f"  {r['w']:<46}{100*r['A']:>+8.2f}%{100*r['B']:>+8.2f}%{r['nA']:>5}{r['nB']:>5}"
          f"{r['pools']:>7}{100*r['life_skill']:>+7.2f}%{100*r['beat']:>5.0f}%"
          f"{r['avg']:>9.2f}{r['per_day']:>6.1f}{100*r['sleep']:>6.1f}%{100*r['off']:>5.0f}%")
json.dump(out, open("data/t2_survivors.json", "w"), indent=1)
print(f"\n  -> data/t2_survivors.json  ({len(out)} wallets)")
