"""What does ENTRY actually cost a copier? Slippage is the last unmodelled execution cost,
and the naive worry (a 2 SOL swap into a $2k memecoin pool) may not apply at all.

A DLMM position can be opened ONE-SIDED: deposit only SOL into bins on one side of the
current price and let price come to you. No swap, so no slippage. That is also why only
60-76% of these wallets' entries have price inside their own range at t=0 -- it is the
strategy, not a mistake (see tools/paper_replay.py).

So measure, per wallet:
  one_sided   share of positions that deposited exactly ONE token -> zero entry slippage
  sol_only    share that deposited only SOL -> zero slippage AND no inventory risk
  tvl         median TVL of the pools the target is in RIGHT NOW. Do NOT measure this
              on historical pools: a memecoin pool traded six months ago is drained
              today, so current TVL reads ~$0 and the position/TVL ratio comes out in the
              millions of percent. Depth at the time is not retrievable; depth today is
              what a copier would actually face, so use the open book.
"""
import json, sys, time, statistics as st, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
SOL = "So11111111111111111111111111111111111111112"
POS = json.load(open("data/t2_positions.json"))
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/shortlist_copyable.json"
SIZE = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0     # copier position, SOL
SOLUSD = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}


def tvl(pool):
    d = get(f"{API}/pools/{pool}")
    try: return float(d.get("tvl") or 0)
    except (TypeError, ValueError): return 0.0


rows = json.load(open(SRC))
WS = [x["w"] if isinstance(x, dict) else x for x in rows]
print(f"  entry cost for a {SIZE:.1f} SOL copier (SOL at ${SOLUSD:.0f})\n")
print(f"  {'wallet':<46}{'n':>6}{'one-sided':>11}{'SOL-only':>10}"
      f"{'open pools':>12}{'med TVL now':>13}{'pos/TVL':>9}{'>10x':>7}")
out = []
for w in WS:
    ps = [p for p in POS.get(w, []) if p.get("isClosed")]
    if len(ps) < 30: continue
    one = solo = 0
    for p in ps:
        d = p["allTimeDeposits"]
        x, y = float(d["tokenX"]["amount"] or 0), float(d["tokenY"]["amount"] or 0)
        if (x > 0) != (y > 0):
            one += 1
            # tokenY is the quote leg in these pools and is SOL for all our finalists
            if y > 0: solo += 1
    op = []
    for pg in range(1, 5):
        d = get(f"{API}/portfolio/open?user={w}&page={pg}&page_size=100")
        op += d.get("pools") or []
        if not d.get("hasNext"): break
    pools = [p["poolAddress"] for p in op][:40]
    with ThreadPoolExecutor(max_workers=10) as ex:
        tv = [t for t in ex.map(tvl, pools) if t > 0]
    med = st.median(tv) if tv else 0
    if not tv:
        print(f"  {w:<46}{len(ps):>6}{100*one/len(ps):>10.0f}%{100*solo/len(ps):>9.0f}%"
              f"{'no open pools':>28}", flush=True)
        out.append({"w": w, "n": len(ps), "one_sided": one/len(ps), "sol_only": solo/len(ps),
                    "med_tvl": None}); continue
    share = (SIZE * SOLUSD / med) if med else 0
    deep = sum(1 for t in tv if t > 10 * SIZE * SOLUSD) / len(tv) if tv else 0
    out.append({"w": w, "n": len(ps), "one_sided": one / len(ps), "sol_only": solo / len(ps),
                "med_tvl": med, "pos_share": share, "deep_share": deep})
    print(f"  {w:<46}{len(ps):>6}{100*one/len(ps):>10.0f}%{100*solo/len(ps):>9.0f}%"
          f"{len(tv):>12}{med:>12,.0f}${100*share:>8.1f}%{100*deep:>6.0f}%", flush=True)
json.dump(out, open("data/entry_cost.json", "w"), indent=1)
print(f"\n  one-sided entries need NO swap, so they carry NO entry slippage.")
print(f"  pos/TVL is the copier's {SIZE:.0f} SOL against the MEDIAN pool; "
      f"'pools>10x' is the share deep enough that it is under 10%.")
