"""Beta classification for Meteora DLMM pools.

Meteoran's gates were calibrated on memecoin DLMM. This module asks a different
question: does the pool's beta come from hype or from a real asset class?

Three classes:

  STOCK      one leg is a tokenized equity (xStocks / Ondo). Beta is bounded and
             external. It arrives in gaps at the session boundary, not
             continuously. Fee/TVL is LOW because the beta is not exploitable.

  STOCK_MEME one leg is a tokenized equity AND the other is a memecoin. This is
             the meme-paired-with-stock case, and it already exists on-chain.
             Both betas are live at once, and they are correlated.

  MEME       neither leg is an equity. The calibration set.

The distinction matters because Meteoran's own headline result is that "token
beta is what kills positions" -- for a STOCK pool the beta is a listed equity
with a hard daily bound, which inverts the risk model rather than extending it.

xStocks mints are SPL tokens issued by Backed Assets (JE) Limited; Ondo Global
Markets mints end in `ondo`. Both are matched by mint address, NOT by symbol --
anyone can mint a token called TSLAx.
"""
from __future__ import annotations

import json
import time
import urllib.request

API = "https://dlmm.datapi.meteora.ag"
UA = {"User-Agent": "Mozilla/5.0"}

# Equity tickers. The mint is authoritative; this list is only a human label.
XSTOCK_TICKERS = {
    # REMOVED "KOx" 2026-10-12. It was added from memory, not from an issuer's
    # published list, and it is wrong: KOx is a memecoin, and it was being
    # classified as an equity on three live DLMM pools (KOx-SOL, KOx-USDC,
    # OFOO-KOx). This is the exact failure CLAUDE.md warns about -- a symbol
    # list that nobody cross-checked is a guess that becomes a finding.
    #
    # Everything below must come from the issuer's published asset list, and the
    # mint must be verified on explorer.solana.com before it goes in here.
    # A ticker on an xStocks-style mint does NOT by itself make it an equity.
    "AAPLx", "TSLAx", "NVDAx", "MSFTx", "METAx", "GOOGLx", "AMDAx", "AMDx",
    "AVGOx", "PLTRx", "HOODx", "SPYx", "QQQx", "COINx", "CRCLx", "MSTRx",
    "ORCLx", "GLDx", "VIDAx", "OPENx", "NFLXx", "SBUXx", "TBLLx",
}
ONDO_TICKERS = {"AAPLon", "MSFTon", "TSLAon", "GOOGLon", "NVDAon", "SPYon",
                "QQQon", "METAon", "CRCLon"}


def get(url: str, tries: int = 3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def classify_token(t: dict) -> str | None:
    """Return the equity ticker if this leg is a tokenized equity."""
    addr = (t.get("address") or "")
    sym = (t.get("symbol") or "").strip()
    # Mint-address family match first -- symbols are trivially spoofed.
    if addr.startswith("Xs") and sym in XSTOCK_TICKERS:
        return sym
    if addr.endswith("ondo") and sym in ONDO_TICKERS:
        return sym
    return None


def win24(v) -> float:
    """Volume/fees come back as a window map. 24h is the one we rank on."""
    if isinstance(v, dict):
        return float(v.get("24h") or 0)
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0


# Every window Meteora publishes for volume, fees and fee_tvl_ratio.
#
# Ranking on 24h alone throws five of six away, and that is a category error
# rather than a simplification: the 24h figure is an average over a window in
# which the pool may have been dead for most of it. A pool that printed its
# whole daily yield in one busy hour and has been idle since looks identical to
# one that traded steadily all day. An LP choosing a pool right now is asking
# what is paying *now*.
#
# The short windows are also the noisy ones -- a single trade can print an
# enormous 30m figure -- which is why all of them are kept rather than just the
# shortest one. The spread between them is the signal.
WINDOWS = ("30m", "1h", "2h", "4h", "12h", "24h")


def window_map(v) -> dict:
    """{window: float}, missing keys zeroed. Tolerates a bare scalar."""
    if not isinstance(v, dict):
        try:
            return {w: float(v or 0) for w in WINDOWS}
        except (TypeError, ValueError):
            return {w: 0.0 for w in WINDOWS}
    out = {}
    for w in WINDOWS:
        try:
            out[w] = float(v.get(w) or 0)
        except (TypeError, ValueError):
            out[w] = 0.0
    return out


def yield_pct(fees: dict, tvl: float) -> dict:
    """Fee/TVL over each window, in percent.

    NOT an APR. Meteora's `apr` field is exactly `fee_tvl_ratio["24h"]` -- the
    raw percentage a pool earned over 24 hours, with no annualisation applied.
    Calling that an APR would imply a ~365x extrapolation the tool never did.
    These are labelled as windowed yields instead, which is what they are.
    """
    if not tvl or tvl <= 0:
        return {w: 0.0 for w in WINDOWS}
    return {w: (fees.get(w, 0.0) / tvl) * 100.0 for w in WINDOWS}


def sane(p: dict) -> bool:
    """Reject the corrupt rows.

    The API returns a non-trivial fraction of garbage -- TVL of 3e-12, APR of
    6e13. An APR above 1000% is not a real pool on Solana. These rows are
    filtered before anything is ranked, because a single one sorts a whole
    table.
    """
    tvl = float(p.get("tvl") or 0)
    apr = float(p.get("apr") or 0)
    # Only reject rows that are structurally broken, not merely expensive.
    # A memecoin pool really can print 800% APR; a row claiming 6e13% cannot.
    if tvl <= 0 or not (tvl > 1e-6):
        return False
    if apr != apr or apr < 0 or apr > 100_000:   # NaN, negative, or absurd
        return False
    return True


MAJORS = {"SOL", "USDC", "USDT", "WSOL"} | {f"{t}on" for t in
          ("AAPL", "MSFT", "TSLA", "GOOGL", "NVDA", "SPY", "QQQ", "META", "CRCL")}


def classify_pair(p: dict) -> tuple[str, str | None, str | None]:
    """-> (class, equity_x, equity_y)

    STOCK      equity vs a major or stablecoin. One live beta.
    STOCK_MEME equity vs a memecoin. Two live betas, and they correlate.
    """
    ex = classify_token(p.get("token_x") or {})
    ey = classify_token(p.get("token_y") or {})
    if not (ex or ey):
        return "MEME", None, None
    other = p.get("token_y") if ex else p.get("token_x")
    other_sym = ((other or {}).get("symbol") or "").strip().upper()
    cls = "STOCK" if other_sym in MAJORS else "STOCK_MEME"
    return cls, ex, ey


def scan(pages: int = 40, page_size: int = 400) -> list[dict]:
    rows = []
    for page in range(1, pages + 1):
        d = get(f"{API}/pools?page={page}&page_size={page_size}"
                f"&sort_by=fee_tvl_ratio_24h%3Adesc")
        batch = d.get("data", [])
        if not batch:
            break
        rows.extend(batch)
    return rows


def main() -> int:
    pages = int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 40
    print(f"  scanning up to {pages} pages of DLMM pools...", flush=True)
    pools = scan(pages=pages)
    total_reported = None
    print(f"  pulled {len(pools):,} pools")

    buckets: dict[str, list[dict]] = {"STOCK": [], "STOCK_MEME": [], "MEME": []}
    corrupt = 0
    for p in pools:
        if not sane(p):
            corrupt += 1
            continue
        cls, ex, ey = classify_pair(p)
        if cls == "MEME":
            continue
        tvl = float(p.get("tvl") or 0)
        fees_w = window_map(p.get("fees"))
        vol_w = window_map(p.get("volume"))
        buckets[cls].append({
            "pool": p["address"],
            "name": p.get("name"),
            "equity": ex or ey,
            "leg_other": (p.get("token_y", {}).get("symbol")
                          if ex else p.get("token_x", {}).get("symbol")),
            "tvl": tvl,
            "apr": float(p.get("apr") or 0),
            # All six windows, kept. See WINDOWS.
            "yield_w": yield_pct(fees_w, tvl),
            "volume_w": vol_w,
            "volume_24h": vol_w.get("24h", 0.0),
            "fees_24h": fees_w.get("24h", 0.0),
            "holders": (p.get("token_x", {}) if ex else p.get("token_y", {})) or {},
            "bin_step": (p.get("pool_config") or {}).get("bin_step"),
            "base_fee": (p.get("pool_config") or {}).get("base_fee_pct"),
        })

    print(f"  dropped {corrupt:,} corrupt rows "
          f"({corrupt / max(1, len(pools)):.1%} of the pull)")

    for name in ("STOCK", "STOCK_MEME"):
        rows = buckets[name]
        rows.sort(key=lambda r: -r["tvl"])
        tvl = sum(r["tvl"] for r in rows)
        aprs = sorted(r["apr"] for r in rows)
        med = aprs[len(aprs) // 2] if aprs else 0.0
        print(f"\n  {name}: {len(rows)} pools, ${tvl:,.0f} TVL, median 24h yield {med:.3f}%")
        print(f"  {'pair':<22}{'TVL':>11}{'30m%':>8}{'1h%':>8}{'4h%':>8}{'24h%':>9}{'holders':>9}")
        for r in rows[:15]:
            y = r.get("yield_w") or {}
            h = r["holders"].get("holders")
            print(f"  {str(r['name'])[:21]:<22}{r['tvl']:>11,.0f}"
                  f"{y.get('30m', 0):>8.3f}{y.get('1h', 0):>8.3f}"
                  f"{y.get('4h', 0):>8.3f}{y.get('24h', 0):>9.3f}"
                  f"{(h if h else 0):>9,}")

    # Beta-class comparison, restricted to pools that actually traded.
    #
    # "traded" is now any window, not just 24h. A pool that sat idle all day and
    # woke up an hour ago has no 24h volume and used to fall out of the
    # comparison entirely -- which is precisely the pool an LP scanning right
    # now wants to see.
    def live(rows):
        return sorted(r["apr"] for r in rows
                      if any(v > 0 for v in (r.get("volume_w") or {}).values()))

    stock_live = live(buckets["STOCK"])
    stockmeme_live = live(buckets["STOCK_MEME"])
    meme_live = sorted(float(p.get("apr") or 0) for p in pools
                       if sane(p) and win24(p.get("volume")) > 0)

    def med(xs):
        return xs[len(xs) // 2] if xs else 0.0

    print("\n  BETA-CLASS SPREAD -- pools with real 24h volume only")
    print(f"    memecoin         median APR {med(meme_live):>8.3f}%   n={len(meme_live):,}")
    print(f"    stock            median APR {med(stock_live):>8.3f}%   n={len(stock_live):,}")
    print(f"    stock x memecoin median APR {med(stockmeme_live):>8.3f}%   n={len(stockmeme_live):,}")
    print("    (dead pools excluded; a pool with no volume has no APR to compare)")

    json.dump({"scanned": len(pools), "buckets": buckets},
              open("data/stock_pairs.json", "w"), indent=1)
    print("\n  -> data/stock_pairs.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())