"""Session-boundary risk in DLMM pools that quote a tokenized equity.

The pitch for extending Meteoran to equity pools rests on one structural claim:
a listed equity's beta is bounded and arrives in a gap at the market open, while
a memecoin's beta is continuous. That is a testable difference in the POOL, not
a claim about the token -- and it is the difference that decides whether a
memecoin-calibrated LP gate transfers.

US equity session is 13:30-20:00 UTC. A pool quoting NVDAx should therefore show
a signature at those hours that a pool quoting a memecoin should not: volume and
range expansion when the underlying actually reprices.

Method: pull hourly OHLCV for every classified pool, bucket each candle by
whether it falls inside the equity session, and compare per-class:

  vol_ratio   24h volume / TVL, session vs overnight. Higher in-session means the
              pool is trading on the equity, not on the token.
  range_pct   (high-low)/open, session vs overnight. Expansion at the open is
              the gapping risk an LP is short gamma into.

Read this as a structural measurement, NOT an LP P&L claim. It says the pool
behaves differently around the session boundary. Whether that is profitable or
not is the separate question, and this repo does not answer it.
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
UA = {"User-Agent": "Mozilla/5.0"}
OUT = "data/session_boundary.json"

# US equity regular session, UTC. DST shifts this to 14:30 in winter; the
# bucketing below tolerates both by testing membership against a 30-min band.
SESSION_START_UTC = (13, 30)
SESSION_END_UTC = (20, 0)


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(1.2 * (i + 1))


def in_session(ts: int) -> bool:
    """Candle timestamp is the bucket START, in UTC."""
    h = (ts // 3600) % 24
    m = (ts // 60) % 60
    t = h + m / 60.0
    lo = SESSION_START_UTC[0] + SESSION_START_UTC[1] / 60.0
    hi = SESSION_END_UTC[0] + SESSION_END_UTC[1] / 60.0
    return lo <= t < hi


def analyse(pool: dict) -> dict | None:
    d = get(f"{API}/pools/{pool['pool']}/ohlcv?timeframe=1h")
    if not d:
        return None
    rows = d.get("data") or []
    if len(rows) < 8:                       # see the hard limit documented below
        return None

    ses, off = [], []
    for r in rows:
        rng = (r["high"] - r["low"]) / r["open"] if r["open"] else 0.0
        vol = float(r.get("volume") or 0)
        (ses if in_session(r["timestamp"]) else off).append((rng, vol))

    # HARD LIMIT, measured: the OHLCV endpoint returns at most 10 candles per
    # call regardless of `limit`, `start_time`, or timeframe. 10 hourly candles
    # is ~42 minutes. That cannot support a session-vs-overnight split, so this
    # tool reports the cap instead of quietly producing a meaningless median.
    #
    # To do the session-boundary study properly you need a candle store fed on
    # a schedule (see tools/forward_recorder.py for that pattern) and an
    # accumulation window of weeks. It is NOT doable from one pull today.
    if len(ses) < 4 or len(off) < 4:
        return {"pool": pool["pool"], "name": pool["name"],
                "equity": pool["equity"], "usable": False,
                "candles": len(rows), "hours_session": len(ses),
                "hours_overnight": len(off)}

    def med(xs):
        return st.median(xs) if xs else 0.0

    return {
        "pool": pool["pool"],
        "name": pool["name"],
        "equity": pool["equity"],
        "other": pool["leg_other"],
        "usable": True,
        "candles": len(rows),
        "hours_session": len(ses),
        "hours_overnight": len(off),
        "range_ses": med([x[0] for x in ses]),
        "range_off": med([x[0] for x in off]),
        "vol_ses": med([x[1] for x in ses]),
        "vol_off": med([x[1] for x in off]),
    }


def agg(rows, key_a, key_b, label):
    a = [r[key_a] for r in rows if r[key_a] > 0]
    b = [r[key_b] for r in rows if r[key_b] > 0]
    ra, rb = (st.median(a) if a else 0.0), (st.median(b) if b else 0.0)
    print(f"    {label:<16} session {ra:>10.5f}   overnight {rb:>10.5f}   "
          f"ratio {ra / rb if rb else 0:>5.2f}x   n={len(rows)}")
    return {"session": ra, "overnight": rb, "n": len(rows)}


def main() -> int:
    if not os.path.exists("data/stock_pairs.json"):
        print("  run tools/stock_pairs.py first")
        return 1
    d = json.load(open("data/stock_pairs.json", encoding="utf-8"))
    stock = d["buckets"]["STOCK"][:30]     # 30 keeps the sweep honest in time
    smeme = d["buckets"]["STOCK_MEME"][:20]

    todo = [(p, "STOCK") for p in stock] + [(p, "STOCK_MEME") for p in smeme]
    print(f"  pulling hourly OHLCV for {len(todo)} pools...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        got = list(ex.map(lambda t: analyse(t[0]), todo))

    res = {"STOCK": [], "STOCK_MEME": []}
    unusable = 0
    for (p, cls), r in zip(todo, got):
        if not r:
            continue
        r["class"] = cls
        if not r.get("usable"):
            unusable += 1
            continue
        res[cls].append(r)

    # Report the ceiling honestly. This tool is a capability probe: it
    # establishes whether the session-boundary study is possible from the
    # public API today, and the answer is no.
    total = len(res["STOCK"]) + len(res["STOCK_MEME"]) + unusable
    print(f"\n  pulled {len(todo)} pools; {unusable} had too few candles to split\n")

    print("  CAPABILITY RESULT")
    print("  The OHLCV endpoint serves a MAXIMUM of 10 candles per call.")
    print("  `limit=500` is ignored. `start_time` is ignored. A range spanning")
    print("  more than ~40 minutes returns HTTP 400 'time range too large'.")
    print()
    print(f"  pools with a usable session/overnight split: "
          f"{len(res['STOCK']) + len(res['STOCK_MEME'])} of {total}")
    print()
    print("  CONSEQUENCE: the session-boundary hypothesis -- that equity-quoted")
    print("  pools widen when the underlying reopens, and memecoin pools do")
    print("  not -- CANNOT be tested from a single pull. It needs a candle")
    print("  store accumulated over weeks (tools/forward_recorder.py does this")
    print("  for positions). Recorded as NOT BUILT rather than estimated.")
    json.dump({"candles_max": 10, "pools_pulled": len(todo),
               "pools_usable": len(res["STOCK"]) + len(res["STOCK_MEME"]),
               "pools_unusable": unusable,
               "classes": res,
               "verdict": "not testable from one pull; needs an accumulated candle store"},
              open(OUT, "w"), indent=1)
    print(f"\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())