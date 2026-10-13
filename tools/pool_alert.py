"""SCAN EVERY POOL CONTINUOUSLY AND PUSH TO THE PHONE WHEN A REAL ENTRY APPEARS.

Read-only. Places nothing. The filters encode what this project measured the hard way:

  rule 25 (111,838 closed positions) -- outcome scales MONOTONICALLY with fee capture.
     <0.5% fee yield -> median +0.0%, 52% win.  >25% -> median +29.4%, 83% win.
     So: rank on fee yield, and require enough of it to clear the 5% threshold fast.

  the NPC/GO lesson (2026-09-26) -- a 24h fee number is BACKWARD-LOOKING. NPC showed
     39.7%/day on 24h while earning $384 in the last hour. It had already died. So the
     ranking metric is the CURRENT 1h rate, and a pool must not be decelerating.

  the entry-price lesson -- high fee yield usually means a pump is happening NOW. Placing
     one-sided SOL under a token that just doubled is bidding for the retrace, which is
     the 21,165-position bucket at -6.94% median / 20% win. So: require a pullback.

GATES (all must pass):
  current 1h rate      >= MIN_RATE  %/day
  trend (1h vs 12h)    >= 0.7       not collapsing
  off 24h high         2-15%        shallow pullback (MEASURED best; 25-50% off is worse)
  24h move             +10% to +150% momentum, not a downtrend and not a vertical
  30m volume           > $0 and 1h volume >= $2,000   <- IS IT ACTUALLY TRADING
  TVL                  >= MIN_TVL
  age                  >= 48h       survived a couple of days
  holders              >= 500       thin holder base means one seller moves the price
  freeze authority     disabled     otherwise the mint can freeze your tokens

Usage:  python3 tools/pool_alert.py [poll_minutes=20] [min_rate=8] [min_tvl=50000]
"""
import json, os, sys, time, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify import push
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
STATE = "data/pool_alert_seen.json"

# --- beta class -------------------------------------------------------
# This scanner ranks EVERY pool and cannot tell an equity-quoted pool from a
# memecoin pool, so it pushes NVDAx-SOL and FROG-SOL with identical treatment.
# Measured 2026-10-12 (tools/stock_pairs.py, 24k-pool pull):
#
#   memecoin          median APR 0.129%   n=2117 live
#   stock             median APR 0.113%   n=  42 live
#   stock x memecoin  median APR 0.020%   n=  31 live
#
# Those are DIFFERENT markets with different beta physics: a listed equity is
# bounded at ~10%/day and reprices in a gap at the session open, a memecoin is
# continuous and unbounded. Ranking them together is the same error as sorting
# a bond book and a memecoin book on one yield column.
#
# So: tag every alert with its class, and let the operator run one class or the
# other. Classification reuses stock_pairs.classify_pair -- one definition of
# "is this an equity", not two that drift apart.
try:
    from stock_pairs import classify_pair
except ImportError:                      # run from repo root, not tools/
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from stock_pairs import classify_pair


def beta_class(p):
    """-> 'stock' | 'stock_meme' | 'meme'. Never raises into the scan loop."""
    try:
        return classify_pair(p)[0].lower()
    except Exception:
        return "unknown"


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return None


def candidates(min_rate, min_tvl):
    """-> list of pools clearing every gate, or None if the scan itself failed."""
    seen, ok = {}, False
    for win in ("1h", "4h", "12h"):
        d = get(f"{API}/pools?page=1&page_size=400"
                f"&sort_by={urllib.parse.quote(f'fee_tvl_ratio_{win}:desc')}")
        if d is None: continue
        ok = True
        for p in (d.get("data") or []): seen[p["address"]] = p
    if not ok: return None                       # scan failed -- do NOT report "nothing found"

    now = time.time()
    rough = []
    for a, p in seen.items():
        # SOL-only book (CLAUDE.md: bankroll is SOL). Skip USDC and other quote tokens.
        # You provide SOL and convert to the volatile token via Bid Ask. Pools that
        # need USDC are out of scope -- 2026-09-28 Slim flagged SV151-USDC, SI-USDC,
        # e/acc-USDC pushes as the wrong side of the book.
        quote_mint = ((p.get("token_y") or {}).get("address") or "").strip()
        if quote_mint != "So11111111111111111111111111111111111111112":
            continue
        tvl = float(p.get("tvl") or 0)
        if tvl < min_tvl or p.get("is_blacklisted"): continue
        if (now - float(p.get("created_at") or 0) / 1000) / 3600 < 48: continue
        ftv = p.get("fee_tvl_ratio") or {}
        # THE CHECK THAT WAS MISSING UNTIL 2026-09-28: raw volume RIGHT NOW.
        # fee_tvl_ratio is a RATIO -- a pool doing literally $0 of volume in the last
        # half hour still ranks if its TVL is small enough. MINI was recommended while
        # doing $0/hour because nothing here looked at absolute flow. A pool with no
        # swaps cannot pay you whatever range you set.
        vol = p.get("volume") or {}
        v30, v1 = float(vol.get("30m") or 0), float(vol.get("1h") or 0)
        if v30 <= 0 or v1 < 2_000: continue
        f1, f12 = float(ftv.get("1h") or 0) * 24, (float(ftv.get("12h") or 0) / 12) * 24
        f30 = float(ftv.get("30m") or 0) * 48
        if f1 < min_rate or f12 <= 0 or f1 / f12 < 0.7: continue
        # The 30m window must CONFIRM the hourly one. Added 2026-09-27 after KLED-SOL
        # read 37.1%/day on 1h ($1,031 of fees) while the last 30m did $41 = 3.0%/day.
        # One large swap inflates a 1h window and fakes an 8.7x "accelerating" trend.
        # Require the most recent half hour to be at least half the hourly rate.
        if f30 < 0.5 * f1: continue
        # SPIKE-VS-TREND, added 2026-09-28 after the operator caught ALLINU-SOL.
        # Comparing 30m to 1h cannot see a burst, because a burst lifts BOTH. ALLINU
        # ran 1.9-7%/day for a full day and then did 32.7%/day in one half hour while
        # price jumped 41% -- 17x its own baseline. The fee rate existed only because of
        # the pump, and the pool was already 12% off that high. Compare the recent rate
        # against the 12-24h BASELINE: real flow builds, a pump spikes.
        f24 = float(ftv.get("24h") or 0)
        if f24 > 0 and f30 / f24 > 5: continue
        rough.append((a, p, tvl, f1, f1 / f12, v30, v1))

    def price(t):
        # v30/v1 must travel IN the tuple. They used to be read from the enclosing
        # loop, so by the time price() ran they held the LAST pool's volume and every
        # alert reported a number belonging to a different pool. Found 2026-09-28.
        a, p, tvl, f1, tr, v30, v1 = t
        n = int(now)
        d = get(f"{API}/pools/{a}/ohlcv?timeframe=1h&start_time={n-86400}&end_time={n}")
        cl = [float(k["close"]) for k in ((d or {}).get("data") or []) if k.get("close")]
        if len(cl) < 12: return None
        cur, hi = cl[-1], max(cl)
        off, mv = 100 * (1 - cur / hi), 100 * (cur / cl[0] - 1)
        # MEASURED 2026-09-27 on 913 real positions opened in the prior 3 days, with the
        # pre-entry price reconstructed from hourly candles. The first two versions of
        # this gate were guesses and both were pointed at the WRONG zone:
        #   24h move into entry:  falling -30..-10% mean -3.4%/44% win  <- old gate allowed
        #                         rising  +10..+50% mean +2.1%/64% win
        #                         pumped  +50..+150% mean +2.7%/72% win <- best
        #                         vertical >+150%   mean -0.9%/75% win  <- fat left tail
        #   off 24h high:         at high <2%  mean -0.5%/36% win
        #                         2-10% off    mean +1.1%/69% win       <- best
        #                         25-50% off   mean -1.2%/61% win       <- old gate required
        # So: momentum with a SHALLOW pullback. Not a deep correction (Beefman is wrong
        # about this), not a vertical, and never a downtrend.
        # TIERED 2026-09-28. The previous flat band let a 2.3-point signal veto a
        # 29-point one: rule 25's fee-yield relationship moves the median outcome from
        # +0.0% to +29.4% (n=111,838), while entry timing moves the mean from -1.2% to
        # +1.1% (n=913). A pool paying 200%/day reaches the >25% fee-yield bucket in
        # under 3 hours, which dwarfs any entry-timing penalty. A pool paying 8%/day
        # does not, so there the entry has to be good. Scale the tolerance with the rate.
        #
        # CORRECTED 2026-09-28: mv_min was -5 for tiers >=15, which let in moves like
        # fone-SOL at -4.9% (in the -30..-10% losing bucket: -3.4% mean, 44% win).
        # The losing bucket starts at -10%, so mv_min must be ABOVE -10 for all tiers.
        # Using -9 keeps a small buffer but blocks the measured losing band.
        #
        # These stay HARD at every tier -- both are measured losers, not preferences:
        # "At the high" was measured at 36% win -- but on tokens that had PUMPED and
        # peaked. For a token that barely moved, "the high" of a flat day is noise, not
        # a top. 2026-09-28: this gate was rejecting ANTHROPIC-SOL (+2.4% on the day,
        # $105k of volume in 30 min, 258 days old, 38k holders) for sitting 0.0% off a
        # high it had never meaningfully risen to. Only apply it to real moves.
        if abs(mv) >= 15 and off < 2: return None
        # RESTORED 2026-09-29. This read -10 and the tier floors read -9, labelled
        # "(Claude measured)". Nothing measured -9 or -10. The measured band is
        # falling -30..-10% -> -3.4% mean / 44% win, so the floor belongs at -20,
        # OUTSIDE that band, not inside it. Do not edit these without a measurement.
        if mv < -20: return None           # falling knife: -3.4% mean, 44% win
        if mv > 200: return None           # vertical: negative mean despite 75% win
        # mv_min was REQUIRING a pump (+10%) at the low tier, which rejected
        # ANTHROPIC-SOL: 258 days old, 38,626 holders, $1.59M daily volume, 12.5%/day
        # and accelerating -- excluded for the crime of being STABLE (+2.4% on the day).
        # The momentum finding says avoid DOWNTRENDS (-3.4% mean / 44% win); it does not
        # say demand a rally. A flat entry costs about -0.5% mean, which ten hours of a
        # 12%/day pool erases several times over. So the floor guards against falling,
        # not against calm.
        if f1 >= 50:      off_max, mv_min = 40, -20
        elif f1 >= 15:    off_max, mv_min = 25, -5
        else:             off_max, mv_min = 15, -5
        if off > off_max or mv < mv_min: return None
        cfg = p.get("pool_config") or {}
        # Token risk fields Meteora already ships in the same payload -- no extra call.
        # Streamflow was checked 2026-09-27 for unlock schedules: it tracks VESTING
        # contracts, has no public JSON API, and pump.fun launches have no vesting at
        # all, so it has nothing on the tokens this scanner finds. Holder count and
        # freeze authority are the risk signals that ARE available.
        tk = p.get("token_x") or {}
        holders = int(tk.get("holders") or 0)
        if holders < 500: return None                 # thin holder base = one seller moves it
        if not tk.get("freeze_authority_disabled", True): return None   # can freeze your exit
        cls, eq_x, eq_y = classify_pair(p)
        return {"name": p.get("name"), "addr": a, "rate": f1, "trend": tr, "tvl": tvl,
                "off": off, "mv": mv, "bin": cfg.get("bin_step"),
                "fee": cfg.get("base_fee_pct"), "price": cur,
                "holders": holders, "mcap": float(tk.get("market_cap") or 0),
                "v30": v30, "v1": v1,
                "class": cls, "equity": eq_x or eq_y}
    with ThreadPoolExecutor(max_workers=10) as ex:
        return [r for r in ex.map(price, rough) if r]


def main():
    mins = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    min_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    # 50k was arbitrary and contradicts rule 24 (pools under $1k TVL returned +4.2% at
    # 66% win). At 0.3-0.5 SOL the operator is <0.5% of a $25k pool, so depth is not the
    # constraint -- holder count is, and that has its own gate. Lowered 2026-09-27 after
    # the floor hid the better of two MINI-SOL pools (28.4%/day vs the 8.1% one it pushed).
    min_tvl = float(sys.argv[3]) if len(sys.argv) > 3 else 20_000
    # 4th arg: which beta class to alert on. "any" (default) keeps the old
    # behaviour. "stock" only pushes equity-quoted pools. "meme" excludes them.
    # "stock_meme" is the pair that measured ~6x worse than either leg alone.
    want = (sys.argv[4] if len(sys.argv) > 4 else "any").lower()
    os.makedirs("data", exist_ok=True)
    seen = json.load(open(STATE)) if os.path.exists(STATE) else {}

    print(f"  scanning every {mins}min | rate>={min_rate}%/day, TVL>=${min_tvl:,.0f}, "
          f"pullback 15-65%, not decelerating")
    print(f"  class: {want.upper()}"
          + ("  (all classes, as before)" if want == "any" else ""))
    print(f"  pushing to ntfy. READ ONLY -- finds pools, places nothing.\n")
    while True:
        c = candidates(min_rate, min_tvl)
        stamp = time.strftime("%H:%M:%S")
        if c is None:
            print(f"  [{stamp}] scan FAILED (API) -- not reporting 'nothing found'")
        else:
            # Beta-class filter. Applied AFTER the gates so the class counts in
            # the log are always the full qualifying set, not a filtered one.
            counts = {}
            for r in c:
                counts[r.get("class", "unknown")] = counts.get(r.get("class", "unknown"), 0) + 1
            if want != "any":
                if want == "meme":
                    c = [r for r in c if r.get("class") != "stock"]
                else:
                    c = [r for r in c if r.get("class") == want]
            c.sort(key=lambda r: -r["rate"])
            fresh = [r for r in c if time.time() - seen.get(r["addr"], 0) > 6 * 3600]
            print(f"  [{stamp}] {len(c)} qualify, {len(fresh)} fresh"
                  + ("  by class: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                     if counts else ""))
            for r in c[:5]:
                print(f"      {r['name'][:18]:<19}{r['rate']:>6.1f}%/day  trend {r['trend']:>4.2f}x  "
                      f"off high {r['off']:>4.1f}%  24h {r['mv']:>+6.1f}%  ${r['tvl']:>9,.0f}  "
                      f"{r['holders']:,} hldrs  30m vol ${r['v30']:,.0f}")
            for r in fresh[:3]:
                tag = {"stock": "EQUITY", "stock_meme": "EQUITY x MEME",
                       "meme": "MEME"}.get(r.get("class"), "")
                body = (f"[{tag}] {r.get('equity') or 'meme beta'} · "
                        f"{r['rate']:.1f}%/day now (trend {r['trend']:.2f}x)\n"
                        f"{r['off']:.0f}% off 24h high, 24h move {r['mv']:+.1f}%\n"
                        f"TVL ${r['tvl']:,.0f}  bin {r['bin']}  fee {r['fee']}%\n"
                        f"{r['holders']:,} holders  mcap ${r['mcap']/1e6:.1f}M\n"
                        f"price {r['price']:.9f}\n"
                        f"-50% floor would be {r['price']*0.5:.9f}\n"
                        f"{r['addr']}")
                push(f"[{tag or 'LP'}] {r['name']}", body, "high", "moneybag")
                seen[r["addr"]] = time.time()
                print(f"      -> PUSHED {r['name']}")
            tmp = STATE + ".tmp"
            with open(tmp, "w") as fh: json.dump(seen, fh)
            os.replace(tmp, STATE)
        time.sleep(mins * 60)


if __name__ == "__main__":
    main()
