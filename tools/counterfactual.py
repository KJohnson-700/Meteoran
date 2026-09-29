"""Score every journalled DECISION, not just the ones that became trades.

A night of forward paper produces ~4,000 journalled rows and ~100 settled trades.
The other 3,900 are rejects, and they are not waste: each carries a slug, a side, and
a real best_ask observed at a real moment. A taker crossing that ask WOULD have
filled -- there is no fill assumption to make, which is the whole reason this is
scoreable when the maker counterfactual is not.

So one night of tape can answer "which band, which offset, which asset pays" across
every cell at once, instead of confirming or failing the single cell the harness
happened to be configured for. This is the same idea as PSB 1's 1.4M settled
rejects, which CLAUDE.md calls its single most useful artefact.

What this DOES NOT do is invent maker fills. A row we never posted has no tick
history, so whether a resting bid would have been hit is unknown and is left
unknown. Taker numbers here are therefore a LOWER bound on a maker strategy: the
maker pays no fee and no spread, but only fills when the market comes to it.

    python3 tools/counterfactual.py data/M5_deep_maker.jsonl
    python3 tools/counterfactual.py data/*.jsonl --by offset
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, ".")
from oracle3.tape import fetch_json, executor, FetchError

GAMMA = "https://gamma-api.polymarket.com"
CACHE = "data/outcome_cache.json"
TAKER = 0.07


def load_cache() -> Dict[str, str]:
    try:
        with open(CACHE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(c: Dict[str, str]) -> None:
    os.makedirs(os.path.dirname(CACHE) or ".", exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(c, fh)
    os.replace(tmp, CACHE)


def outcome_of(slug: str) -> Optional[str]:
    try:
        ev = fetch_json(f"{GAMMA}/events?slug={slug}")
    except (FetchError, OSError, ValueError):
        return None
    if not ev or not ev[0].get("markets"):
        return None
    m = ev[0]["markets"][0]
    if not m.get("closed"):
        return None
    try:
        prices = json.loads(m.get("outcomePrices") or "[]")
    except json.JSONDecodeError:
        return None
    return ("UP" if prices[0] == "1" else "DOWN") if prices else None


def resolve(slugs: List[str], cache: Dict[str, str]) -> Dict[str, str]:
    todo = [s for s in slugs if s not in cache]
    if todo:
        print(f"  resolving {len(todo)} unseen slugs...", file=sys.stderr)
        for slug, res in zip(todo, executor().map(outcome_of, todo)):
            if res:
                cache[slug] = res
        save_cache(cache)
    return cache


def taker_roi(price: float, won: bool) -> float:
    """ROI on one unit of stake for a taker crossing at `price`, held to settlement.
    Fee is the venue formula, 0.07*p*(1-p) per share = 7%*(1-p) of notional."""
    fee = TAKER * (1 - price)
    return ((1.0 / price) - 1.0 - fee) if won else (-1.0 - fee)


def clustered(pairs: List[tuple]) -> tuple:
    """(n_trades, n_clusters, mean%, lo%, hi%) with CIs clustered on window_start.
    Seven assets settling on one 5-minute move are not seven independent bets."""
    g = collections.defaultdict(list)
    for ws, x in pairs:
        g[ws].append(x)
    m = [sum(v) / len(v) for v in g.values()]
    n = len(m)
    mu = sum(m) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in m) / n) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n else 0.0
    return len(pairs), n, 100 * mu, 100 * (mu - 1.96 * se), 100 * (mu + 1.96 * se)


def rows_from(paths: List[str]) -> List[Dict[str, Any]]:
    out = []
    for p in paths:
        for line in open(p):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            # every row that saw a book: rejects included, which is the point
            if r.get("slug") and r.get("best_ask") and r.get("side") or \
               (r.get("slug") and r.get("best_ask") and r.get("favorite_side")):
                out.append(r)
    return out


def report(rows, cache, key, label, floor=0.0, ceil=1.0) -> None:
    buckets = collections.defaultdict(list)
    for r in rows:
        side = r.get("side") or r.get("favorite_side")
        res = cache.get(r["slug"])
        if not side or not res:
            continue
        px = r["best_ask"]
        if not (floor <= px <= ceil):
            continue
        buckets[key(r)].append((r["window_start"], taker_roi(px, res == side)))
    print(f"\n  {label:<14}{'trades':>8}{'windows':>9}{'net/trade':>11}{'95% CI':>24}")
    for k in sorted(buckets, key=lambda x: (x is None, x)):
        p = buckets[k]
        if len(p) < 30:
            continue
        n, nc, mu, lo, hi = clustered(p)
        flag = "  <<< CI EXCLUDES ZERO" if lo > 0 or hi < 0 else ""
        print(f"  {str(k):<14}{n:>8}{nc:>9}{mu:>10.2f}%  [{lo:>7.2f},{hi:>7.2f}]{flag}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("journals", nargs="+")
    ap.add_argument("--band-step", type=float, default=0.05)
    a = ap.parse_args()

    rows = rows_from(a.journals)
    if not rows:
        print("no scoreable rows", file=sys.stderr)
        return 1
    cache = resolve(sorted({r["slug"] for r in rows}), load_cache())
    scored = [r for r in rows if cache.get(r["slug"])]
    print(f"{len(rows)} journalled decisions, {len(scored)} with a settled outcome "
          f"({100*len(scored)/len(rows):.0f}%)")
    print("TAKER counterfactual: cross the observed ask, hold to settlement, real fee.")
    print("No fill assumption is made -- that is why rejects are scoreable here.")

    step = a.band_step
    report(scored, cache, lambda r: f"{step*int(r['best_ask']/step):.2f}-"
                                    f"{step*int(r['best_ask']/step)+step:.2f}", "ask band")
    report(scored, cache, lambda r: r.get("elapsed"), "entry offset")
    report(scored, cache, lambda r: r.get("asset"), "asset")
    report(scored, cache, lambda r: r.get("window"), "timeframe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
