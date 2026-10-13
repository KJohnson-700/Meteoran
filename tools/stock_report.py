"""Static HTML report for the tokenized-equity DLMM result.

    python3 tools/stock_pairs.py 60     # produces data/stock_pairs.json
    python3 tools/stock_report.py       # -> reports/stock-pairs.html

One self-contained file. No server, no wallet, no Python needed to VIEW it --
the judges can open it straight from the repo or the raw GitHub URL.

Why a static export when tools/dashboard.py already serves a live board: that one
is scoped to the operator's own open positions and needs a wallet address, which
is gitignored. This one is the public result of a measurement anyone can re-run,
so it has to stand on its own with no credentials.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "stock_pairs.json")
# NOT reports/ -- that directory is gitignored because the rendered operator
# dashboards there contain a wallet address and open positions. This export has
# neither, so it lives in docs/ where it is safe to commit and serve.
OUT = os.path.join(ROOT, "docs", "stock-pairs.html")


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0.0


def live(rows):
    return [r for r in rows if r.get("volume_24h", 0) > 0]


def rows_html(rows, limit=18):
    out = []
    for r in rows[:limit]:
        tvl = r["tvl"]
        apr = r["apr"]
        vtvl = r["volume_24h"] / tvl if tvl else 0
        h = (r.get("holders") or {}).get("holders") or 0
        out.append(
            f"<tr><td class='pair'>{r['name']}</td>"
            f"<td class='num'>${tvl:,.0f}</td>"
            f"<td class='num'>{apr:.3f}%</td>"
            f"<td class='num'>{vtvl:.2f}</td>"
            f"<td class='num'>{h:,}</td></tr>")
    return "\n".join(out)


def main() -> int:
    if not os.path.exists(SRC):
        print(f"  missing {SRC} -- run: python3 tools/stock_pairs.py 60")
        return 1

    d = json.load(open(SRC, encoding="utf-8"))
    stock = d["buckets"]["STOCK"]
    smeme = d["buckets"]["STOCK_MEME"]
    scanned = d["scanned"]

    stock_live = [r["apr"] for r in live(stock)]
    smeme_live = [r["apr"] for r in live(smeme)]
    stock_tvl = sum(r["tvl"] for r in stock)
    smeme_tvl = sum(r["tvl"] for r in smeme)

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meteoran — DLMM beta-class report</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#0b0d12; color:#e6e9ef;
         font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:48px 24px 80px; }}
  h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:-.02em; }}
  .sub {{ color:#8b93a7; margin:0 0 36px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(168px,1fr));
           gap:12px; margin-bottom:40px; }}
  .kpi {{ background:#12151d; border:1px solid #1e2431; border-radius:12px; padding:16px; }}
  .kpi b {{ display:block; font-size:26px; letter-spacing:-.02em; }}
  .kpi span {{ color:#8b93a7; font-size:12.5px; text-transform:uppercase;
               letter-spacing:.07em; }}
  h2 {{ font-size:17px; margin:40px 0 6px; }}
  .note {{ color:#8b93a7; font-size:13.5px; margin:0 0 14px; }}
  table {{ width:100%; border-collapse:collapse; background:#12151d;
           border:1px solid #1e2431; border-radius:12px; overflow:hidden; }}
  th,td {{ padding:10px 14px; text-align:left; border-bottom:1px solid #1a1f2b; }}
  th {{ font-size:11.5px; text-transform:uppercase; letter-spacing:.08em;
        color:#8b93a7; font-weight:600; }}
  tr:last-child td {{ border-bottom:none; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .pair {{ font-weight:600; }}
  .cmp {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
          gap:12px; margin:18px 0 8px; }}
  .card {{ background:#12151d; border:1px solid #1e2431; border-radius:12px;
           padding:18px; }}
  .card .v {{ font-size:30px; font-weight:700; letter-spacing:-.02em; }}
  .card .k {{ color:#8b93a7; font-size:12.5px; text-transform:uppercase;
              letter-spacing:.07em; margin-top:4px; }}
  .card .m {{ color:#8b93a7; font-size:12.5px; margin-top:6px; }}
  .bad {{ color:#ff7a6b; }} .good {{ color:#4ade80; }}
  .flag {{ border-left:3px solid #ff7a6b; background:#171a22; padding:12px 16px;
           border-radius:0 10px 10px 0; margin:20px 0; font-size:13.5px; }}
  code {{ background:#171a22; padding:2px 6px; border-radius:5px; font-size:13px; }}
  footer {{ margin-top:48px; color:#6b7385; font-size:13px; }}
  a {{ color:#7aa2ff; }}
</style></head><body><div class="wrap">

<h1>Meteoran — DLMM beta-class report</h1>
<p class="sub">Do DLMM LP gates transfer from memecoins to tokenized equity?
Live pull, {scanned:,} pools, no wallet, read-only.</p>

<div class="kpis">
  <div class="kpi"><b>{len(stock)}</b><span>stock pools</span></div>
  <div class="kpi"><b>${stock_tvl:,.0f}</b><span>stock TVL</span></div>
  <div class="kpi"><b>{len(smeme)}</b><span>stock x meme</span></div>
  <div class="kpi"><b>${smeme_tvl:,.0f}</b><span>stock x meme TVL</span></div>
</div>

<h2>Median APR — live pools only</h2>
<p class="note">Dead pools excluded: a pool with no 24h volume has no APR to
compare, and including them drags every median toward zero.</p>
<div class="cmp">
  <div class="card"><div class="v">{med(stock_live):.3f}%</div>
    <div class="k">stock</div><div class="m">n = {len(stock_live)}</div></div>
  <div class="card"><div class="v bad">{med(smeme_live):.3f}%</div>
    <div class="k">stock x memecoin</div>
    <div class="m">n = {len(smeme_live)} — ~{(med(stock_live)/max(med(smeme_live),1e-9)):.0f}x worse</div></div>
</div>
<p class="note">Meme-paired-with-stock is the worst class for an LP by roughly
six times. Two correlated betas on one pool, and the fee share does not cover
the variance.</p>

<h2>Stock-quoted pools, by TVL</h2>
<p class="note">Beta is the listed equity: bounded at ~10%/day, and it arrives
in a gap at the session boundary rather than continuously.</p>
<table><thead><tr><th>pair</th><th class="num">TVL</th><th class="num">APR</th>
<th class="num">vol24/TVL</th><th class="num">holders</th></tr></thead>
<tbody>{rows_html(stock)}</tbody></table>

<h2>Stock x memecoin pools, by TVL</h2>
<p class="note">Both betas live at once. Note GOOGLx-GOOGLon: the same company
across two issuers, in two liquidity silos. And STONK-NVDAx: meme-paired-with-
stock, already live, bottom decile by yield.</p>
<table><thead><tr><th>pair</th><th class="num">TVL</th><th class="num">APR</th>
<th class="num">vol24/TVL</th><th class="num">holders</th></tr></thead>
<tbody>{rows_html(smeme)}</tbody></table>

<div class="flag"><b>Data quality.</b> A large fraction of the raw
<code>/pools</code> pull is structurally corrupt — TVL of 3e-12, APR of 6e13.
Every figure on this page is post-filter. A single unfiltered row sorts an
entire table, which is why every public leaderboard on this venue is
untrustworthy.</div>

<h2>What this is not</h2>
<p class="note">Not a strategy, not a bot, not a ranking product. It is a
pool-level cross-section from one pull: no wallet-level skill measurement, no
time series, no persistence test. A first measurement with a direction.</p>

<footer>Reproduce: <code>python3 tools/stock_pairs.py 60</code> ·
Source <a href="https://github.com/KJohnson-700/Meteoran">github.com/KJohnson-700/Meteoran</a> ·
read-only, standard library only</footer>

</div></body></html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  -> {OUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())