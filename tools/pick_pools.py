"""Pick which pools to hand to an external pool-scanner (Valyze, tracklp) for
WALLET ENUMERATION.

Why this exists: the Meteora datapi is a lookup, never a listing -- every endpoint
requires `user`, so it cannot tell us who else LP'd anywhere. A pool scanner can.
That is the ONLY thing worth buying from these products; their ratings break rules 7
and 8. So we choose the pools, harvest the wallet lists, and measure them ourselves.

Selection logic -- we want pools whose LP roster is enriched for skill:
  * used by 2+ of our measured finalists   -> independent confirmation of a good venue
  * capital they actually committed there  -> conviction, not a toe-dip
  * vs-HODL skill generated there          -> the pool paid real LP edge, not token beta
  * RECENT                                 -> a dead memecoin pool has no roster left

Recency is a hard gate, not a tiebreaker. Everything else is a sort.
"""
import json, sys, time, collections, datetime
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

MAX_AGE_DAYS = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
NOW = max(p.get("lastClosedAt") or 0
          for ps in json.load(open("data/three_pools.json")).values() for p in ps)

data = json.load(open("data/three_pools.json"))
pools = collections.defaultdict(lambda: dict(
    wallets=set(), n=0, dep=0.0, pnl=0.0, skill=0.0, fees=0.0, last=0, meta=None))

for w, ps in data.items():
    for p in ps:
        a = p.get("poolAddress")
        if not a: continue
        e = pools[a]
        e["wallets"].add(w); e["n"] += 1
        e["dep"]  += f(p, "totalDepositSol")
        e["pnl"]  += f(p, "pnlSol")
        e["fees"] += f(p, "totalFeeSol")
        r = vs_hodl(p)
        if r: e["skill"] += r[0]
        e["last"] = max(e["last"], p.get("lastClosedAt") or 0)
        e["meta"] = p

rows = []
for a, e in pools.items():
    age = (NOW - e["last"]) / 86400
    if age > MAX_AGE_DAYS: continue
    if e["dep"] <= 0: continue
    m = e["meta"]
    rows.append(dict(
        pool=a, age=age, wallets=len(e["wallets"]), n=e["n"], dep=e["dep"],
        pnl=e["pnl"], skill=e["skill"], fees=e["fees"],
        pair=f'{m.get("tokenX")}/{m.get("tokenY")}',
        binStep=m.get("binStep"), baseFee=m.get("baseFee"),
        who="+".join(sorted(e["wallets"]))))

# multi-finalist pools first, then by capital committed
rows.sort(key=lambda r: (-r["wallets"], -r["dep"]))

print(f"\n  {len(rows)} pools within {MAX_AGE_DAYS:.0f}d of the finalists' last close "
      f"({datetime.datetime.utcfromtimestamp(NOW):%Y-%m-%d}), of {len(pools)} total\n")
print(f"  {'#':>3} {'pool address':<44} {'pair':<18} {'LPs':>3} {'pos':>4} "
      f"{'dep SOL':>9} {'skill':>8} {'age d':>6}  who")
for i, r in enumerate(rows[:40], 1):
    print(f"  {i:>3} {r['pool']:<44} {r['pair'][:18]:<18} {r['wallets']:>3} {r['n']:>4} "
          f"{r['dep']:>9,.0f} {r['skill']:>+8.1f} {r['age']:>6.1f}  {r['who']}")

json.dump(rows, open("data/pick_pools.json", "w"), indent=1)
print(f"\n  -> data/pick_pools.json ({len(rows)} rows)")
