"""Headline figures, straight from the last pull.

    python3 tools/_summary.py          # print
    python3 tools/_summary.py --sync   # rewrite the figures inside SUBMISSION.md

The numbers move every 30 minutes, and a submission form cannot be edited
after it is sent. So the copy in SUBMISSION.md is not written by hand: --sync
regenerates the one paragraph that quotes live figures from the same JSON the
report is rendered from. Hand-maintained numbers in a file that has to be
correct at one specific moment is a footgun, not a convenience.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "stock_pairs.json")
SUB = os.path.join(ROOT, "SUBMISSION.md")

# Imported, not duplicated. The report ranks pools at or above this floor, so
# the copy pasted into the submission form has to use the same number -- a
# --sync that reported different figures from the page it is describing would
# be worse than having no sync at all.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_report import MIN_TVL, RANK_WINDOW

BEGIN = "<!-- live-figures:begin -->"
END = "<!-- live-figures:end -->"


def live(rows, key="volume_24h"):
    return [r["apr"] for r in rows if r.get(key, 0) > 0]


def med(xs):
    return sorted(xs)[len(xs) // 2] if xs else 0.0


def yld(r, w="24h"):
    """Windowed fee/TVL yield in percent. Mirrors stock_report exactly."""
    y = r.get("yield_w")
    if not y:
        return float(r.get("apr") or 0.0) if w == "24h" else 0.0
    return float(y.get(w) or 0.0)


def traded(r):
    v = r.get("volume_w")
    if not v:
        return r.get("volume_24h", 0) > 0
    return any(x > 0 for x in v.values())


def figures(d):
    # Same floor AND same ranking window the page uses, so these numbers and the
    # page can never describe different things.
    rank = lambda rows: [r for r in rows if r["tvl"] >= MIN_TVL]
    s, m = rank(d["buckets"]["STOCK"]), rank(d["buckets"]["STOCK_MEME"])
    sl = [yld(r, RANK_WINDOW) for r in s if traded(r)]
    ml = [yld(r, RANK_WINDOW) for r in m if traded(r)]
    ms, mm = med(sl), med(ml)
    # A ratio only means something when the denominator is above zero. On the
    # 1h window the median stock x memecoin pool can earn exactly nothing, and
    # dividing by that would print a confident "0.0x" for what is really an
    # undefined quantity. Report the zero instead of a number derived from it.
    if mm > 0:
        ratio = ms / mm
        ratio_txt = f"{ratio:.0f}x" if ratio >= 10 else f"{ratio:.1f}x"
    elif ms > 0:
        ratio = float("inf")
        ratio_txt = None
    else:
        ratio = float("nan")
        ratio_txt = None
    return {
        "scanned": d["scanned"],
        "s_n": len(s), "s_tvl": sum(r["tvl"] for r in s),
        "m_n": len(m), "m_tvl": sum(r["tvl"] for r in m),
        "s_med": ms, "m_med": mm, "s_live": len(sl), "m_live": len(ml),
        "ratio": ratio, "ratio_txt": ratio_txt,
        "floor": MIN_TVL, "win": RANK_WINDOW,
    }


def paragraph(f):
    """Every claim here is computed from stock_pairs.json.

    Deliberately cites nothing from the memecoin study: that median comes from
    a different pull, and a submission that mixes two datasets into one
    sentence without saying so is asking to be disbelieved.
    """
    # The comparison sentence, chosen so it is never false. If the denominator
    # median is zero there is no ratio to state, and printing one anyway --
    # including a formatted "0.0x" -- would put a fabricated number into a
    # submission form.
    if f["ratio_txt"]:
        cmp_sentence = (
            f"Pairing a stock with a memecoin pays about "
            f"{f['ratio_txt']} less on the same window")
    elif f["m_med"] == 0 and f["s_med"] > 0:
        cmp_sentence = (
            f"The median stock×memecoin pool earned nothing at all over that "
            f"window — so there is no ratio to quote, only a difference "
            f"between a market that trades and one that does not")
    else:
        cmp_sentence = ""

    return (
        f"{BEGIN}\n"
        f"Nobody has run that test on tokenized equity. Of "
        f"{f['scanned']:,} DLMM pools scanned, {f['s_n'] + f['m_n']} hold at "
        f"least ${f['floor']:,.0f} and quote an equity token: {f['s_n']} "
        f"stock-quoted, {f['m_n']} pairing a stock against a memecoin. Ranked "
        f"on the same rolling windows the gates read rather than a 24-hour "
        f"average — a pool that paid its whole day in one busy hour and has "
        f"been idle since looks identical, on a 24h view, to one that traded "
        f"steadily. On pools that actually traded, median {f['win']} yield is "
        f"{f['s_med']:.4f}% for stock-quoted pools (n={f['s_live']}) and "
        f"{f['m_med']:.4f}% for stock×memecoin (n={f['m_live']}). "
        f"{cmp_sentence}. The equity leg is the same either way, so the entire "
        f"difference is the other leg.\n"
        f"{END}"
    )


def sync(f):
    if not os.path.exists(SUB):
        print(f"  missing {SUB}")
        return 1
    src = io.open(SUB, encoding="utf-8").read()
    if BEGIN not in src or END not in src:
        print(f"  {SUB} has no {BEGIN} ... {END} markers -- not syncing")
        return 1
    new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                 lambda _: paragraph(f), src, flags=re.S)
    if new == src:
        print("  SUBMISSION.md already current")
        return 0
    io.open(SUB, "w", encoding="utf-8", newline="\n").write(new)
    print("  SUBMISSION.md figures updated from data/stock_pairs.json")
    return 0


def main() -> int:
    if not os.path.exists(SRC):
        print(f"  missing {SRC} -- run: python3 tools/stock_pairs.py 60")
        return 1
    d = json.load(open(SRC, encoding="utf-8"))
    f = figures(d)

    if "--sync" in sys.argv:
        return sync(f)

    print("scanned:", f"{f['scanned']:,}")
    print(f"rank floor ${f['floor']:,.0f}   ranking window: {f['win']}")
    print(f"STOCK      {f['s_n']:>3} pools  ${f['s_tvl']:,.0f} TVL")
    print(f"STOCK_MEME {f['m_n']:>3} pools  ${f['m_tvl']:,.0f} TVL")
    print(f"median {f['win']} yield stock       {f['s_med']:.4f}%  (n={f['s_live']})")
    print(f"median {f['win']} yield stockxmeme  {f['m_med']:.4f}%  (n={f['m_live']})")
    print(f"ratio                           {f['ratio_txt'] or 'undefined (denominator median is 0)'}")
    print("\ntop 6 by", f["win"], "yield:")
    rank = lambda rows: [r for r in rows if r["tvl"] >= MIN_TVL]
    for r in sorted(rank(d["buckets"]["STOCK"] + rank(d["buckets"]["STOCK_MEME"])),
                    key=lambda r: -yld(r, RANK_WINDOW))[:6]:
        print(f"  {r['name']:<18}{yld(r, RANK_WINDOW):>8.3f}%  "
              f"24h {yld(r, '24h'):>7.3f}%  ${r['tvl']:>9,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())