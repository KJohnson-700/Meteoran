"""PICK YOUR OWN POOL. Ranks live Meteora DLMM pools by expected fee yield.

Built 2026-09-26, and it rests on the single strongest finding in this project.
Measured over 111,838 CLOSED positions across 179 wallets, outcome scales
MONOTONICALLY with how much a position actually earned in fees:

    fee yield <0.5%  ->  median  +0.0%,  52% win   (40% of all positions)
    fee yield 2-5%   ->  median  +2.3%,  73% win
    fee yield 5-10%  ->  median  +4.7%,  69% win
    fee yield 10-25% ->  median  +8.9%,  69% win
    fee yield >25%   ->  median +29.4%,  83% win   <- and mean +34.4%

Fee capture is not a bonus on top of the trade. It IS the trade. A position that
earns nothing is a coin flip that loses money on average, whatever the token does.

`/pools` exposes `fee_tvl_ratio` per timeframe -- fees paid per unit of TVL, i.e.
exactly the yield you would earn per SOL deposited if you held the whole pool's
range. It needs NO wallet (this project's notes wrongly said the API cannot
enumerate; /pools lists all 132,159 of them and sorts server-side).

    your fee yield ~= fee_tvl_ratio x (hours held) x (your concentration factor)

Concentration factor is why LPs beat the headline APR: liquidity in a narrow band
around the active bin earns the whole pool's fees on a fraction of the capital.

WHAT THIS TOOL CANNOT TELL YOU: whether the token is about to collapse. Fee yield
predicts the fee side. Token beta -- not IL -- is what kills positions (measured:
fees cover IL 3.74x, so IL is NOT the enemy). Read the sanity columns and size small.

Usage:
    python3 tools/pick_pool.py                    # top pools by 1h fee/TVL
    python3 tools/pick_pool.py 6h 40              # different window, more rows
    python3 tools/pick_pool.py 1h 25 --min-tvl 20000
"""
import json, sys, urllib.request, urllib.parse, time

API = "https://dlmm.datapi.meteora.ag"
# only these are server-sortable; 6h and 8h exist in the payload but 400 on sort_by
WINDOWS = ("30m", "1h", "2h", "4h", "12h", "24h")


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(4):
        try:
            with urllib.request.urlopen(r, timeout=30) as x: return json.loads(x.read())
        except Exception: time.sleep(0.4 * (a + 1))
    return {}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    win = args[0] if args and args[0] in WINDOWS else "1h"
    rows_wanted = int(args[1]) if len(args) > 1 else 25
    min_tvl = 5_000.0
    if "--min-tvl" in sys.argv:
        min_tvl = float(sys.argv[sys.argv.index("--min-tvl") + 1])

    sort = f"fee_tvl_ratio_{win}:desc"
    d = get(f"{API}/pools?page=1&page_size=400&sort_by={urllib.parse.quote(sort)}")
    pools = d.get("data") or []
    if not pools:
        sys.exit(f"no data for sort_by={sort}")

    hours = {"30m": .5, "1h": 1, "2h": 2, "4h": 4, "12h": 12, "24h": 24}[win]
    out = []
    for p in pools:
        tvl = float(p.get("tvl") or 0)
        if tvl < min_tvl or p.get("is_blacklisted"): continue
        ftv = float((p.get("fee_tvl_ratio") or {}).get(win) or 0)
        vol = float((p.get("volume") or {}).get(win) or 0)
        if ftv <= 0: continue
        cfg = p.get("pool_config") or {}
        age_h = (time.time() - float(p.get("created_at") or 0) / 1000) / 3600
        out.append({
            "name": p.get("name", "?"), "addr": p.get("address", ""),
            # fee_tvl_ratio is ALREADY A PERCENT -- verified against fees/TVL on 6 pools,
            # ratio/calc == 1.00 exactly. Multiplying by 100 inflates it 100x.
            "ftv": ftv, "per_day": ftv * (24 / hours),
            "tvl": tvl, "vol": vol, "vol_tvl": vol / tvl,
            "bin": cfg.get("bin_step"), "fee": cfg.get("base_fee_pct"),
            "age_h": age_h})
    out.sort(key=lambda r: -r["ftv"])

    print(f"\n  POOLS BY FEE YIELD -- {win} window, TVL >= ${min_tvl:,.0f}, "
          f"{len(out)} of {d.get('total', 0):,} pools qualify\n")
    print(f"  {'pool':<20}{'fee/TVL':>9}{'~%/day':>9}{'TVL':>12}{'vol/TVL':>9}"
          f"{'bin':>5}{'fee%':>7}{'age':>8}")
    for r in out[:rows_wanted]:
        age = f"{r['age_h']/24:.0f}d" if r["age_h"] >= 48 else f"{r['age_h']:.0f}h"
        print(f"  {r['name'][:19]:<20}{r['ftv']:>8.3f}%{r['per_day']:>8.1f}%"
              f"{r['tvl']:>12,.0f}{r['vol_tvl']:>9.2f}{str(r['bin']):>5}"
              f"{r['fee'] or 0:>7.2f}{age:>8}")
    print(f"\n  fee/TVL is what you earn per SOL deposited over the {win} window at FULL-RANGE")
    print(f"  liquidity. Concentrating near the active bin multiplies it; going out of range")
    print(f"  zeroes it. The 111k-position table says aim for a position that clears 5%+ in")
    print(f"  fees before you exit -- below that the median outcome is a coin flip.")
    print(f"\n  SANITY: high fee/TVL on a tiny young pool usually means one big swap, not flow.")
    print(f"  Prefer vol/TVL above ~1 with age over a day. This tool cannot see a rug coming.")


if __name__ == "__main__":
    main()
