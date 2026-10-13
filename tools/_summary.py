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
from stock_report import MIN_TVL

BEGIN = "<!-- live-figures:begin -->"
END = "<!-- live-figures:end -->"


def live(rows, key="volume_24h"):
    return [r["apr"] for r in rows if r.get(key, 0) > 0]


def med(xs):
    return sorted(xs)[len(xs) // 2] if xs else 0.0


def figures(d):
    # Same floor the page ranks with, so these numbers and the page agree.
    rank = lambda rows: [r for r in rows if r["tvl"] >= MIN_TVL]
    s, m = rank(d["buckets"]["STOCK"]), rank(d["buckets"]["STOCK_MEME"])
    sl, ml = live(s), live(m)
    ms, mm = med(sl), med(ml)
    ratio = ms / mm if mm > 0 else 0.0
    return {
        "scanned": d["scanned"],
        "s_n": len(s), "s_tvl": sum(r["tvl"] for r in s),
        "m_n": len(m), "m_tvl": sum(r["tvl"] for r in m),
        "s_med": ms, "m_med": mm, "s_live": len(sl), "m_live": len(ml),
        "ratio": ratio,
        "ratio_txt": (f"{ratio:.0f}x" if ratio >= 10 else f"{ratio:.1f}x")
        if ratio == ratio else "n/a",
        "floor": MIN_TVL,
    }


def paragraph(f):
    """Every claim here is computed from stock_pairs.json.

    Deliberately cites nothing from the memecoin study: that median comes from
    a different pull, and a submission that mixes two datasets into one
    sentence without saying so is asking to be disbelieved.
    """
    return (
        f"{BEGIN}\n"
        f"Nobody has run that test on tokenized equity. Of "
        f"{f['scanned']:,} DLMM pools scanned, {f['s_n'] + f['m_n']} hold at "
        f"least ${f['floor']:,.0f} and quote an equity token: {f['s_n']} "
        f"stock-quoted, {f['m_n']} pairing a stock against a memecoin. On "
        f"pools that actually traded, median APR runs {f['s_med']:.3f}% for "
        f"stock-quoted pools (n={f['s_live']}) and {f['m_med']:.3f}% for "
        f"stock×memecoin (n={f['m_live']}). Pairing a stock with a memecoin "
        f"pays about {f['ratio_txt']} less — the same equity beta either way, "
        f"so the whole difference is the other leg. Two correlated betas on "
        f"one pool, and the fee share stops covering the variance.\n"
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
    print(f"STOCK      {f['s_n']:>3} pools  ${f['s_tvl']:,.0f} TVL")
    print(f"STOCK_MEME {f['m_n']:>3} pools  ${f['m_tvl']:,.0f} TVL")
    print(f"median APR stock       {f['s_med']:.3f}%  (n={f['s_live']})")
    print(f"median APR stockxmeme  {f['m_med']:.3f}%  (n={f['m_live']})")
    print(f"ratio                  {f['ratio_txt']}")
    print("\ntop 6 by APR:")
    rank = lambda rows: [r for r in rows if r["tvl"] >= MIN_TVL]
    for r in sorted(rank(d["buckets"]["STOCK"] + rank(d["buckets"]["STOCK_MEME"])),
                    key=lambda r: -r["apr"])[:6]:
        print(f"  {r['name']:<18} {r['apr']:>7.3f}%  ${r['tvl']:>10,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())