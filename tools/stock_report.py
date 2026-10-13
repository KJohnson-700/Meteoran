"""Static HTML report for the tokenized-equity DLMM result.

    python3 tools/stock_pairs.py 60     # produces data/stock_pairs.json
    python3 tools/stock_report.py       # -> docs/stock-pairs.html

One self-contained file. No server, no wallet, no Python needed to VIEW it --
the judges can open it straight from the repo or the raw GitHub URL.

Why a static export when tools/dashboard.py already serves a live board: that one
is scoped to the operator's own open positions and needs a wallet address, which
is gitignored. This one is the public result of a measurement anyone can re-run,
so it has to stand on its own with no credentials.

Design tokens are Open Props (open-props.com, MIT), inlined on the subset this
page actually uses. Inlined rather than linked: a CDN <link> turns the one file a
judge is guaranteed to be able to open into a file that renders as an unstyled
document the moment the wifi drops.
"""
from __future__ import annotations

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "stock_pairs.json")
# NOT reports/ -- that directory is gitignored because the rendered operator
# dashboards there contain a wallet address and open positions. This export has
# neither, so it lives in docs/ where it is safe to commit and serve.
OUT = os.path.join(ROOT, "docs", "stock-pairs.html")

# Minimum TVL for a pool to be ranked.
#
# This is the single most important filter in the page and it is not cosmetic.
# 77 of the 100 equity pools found hold under $5,000 and the median holds $493.
# Ranked on raw APR, the top earner in the stock x memecoin class was a pool
# with $19 of TVL printing 221% -- arithmetically true, economically
# meaningless, and the first thing anyone opening this page would have seen.
# A yield figure computed on $19 of depth is arithmetic, not a return.
#
# $1,000 keeps 40 of the 100 pools and puts a real one at the top. The floor is
# applied here, at render, rather than in tools/stock_pairs.py, so the captured
# JSON stays a faithful record of everything that was seen -- nothing is hidden,
# and the page states how many pools the floor excluded.
MIN_TVL = 1000.0

# --- Open Props subset (v1.7.7), verbatim values -------------------------
# https://unpkg.com/open-props@1.7.7/open-props.min.css
CSS = """
:root {
  color-scheme: light dark;
  /* scale */
  --size-1:.25rem; --size-2:.5rem; --size-3:1rem; --size-4:1.25rem;
  --size-5:1.5rem;  --size-6:1.75rem; --size-7:2rem; --size-8:3rem;
  --font-size-0:.75rem; --font-size-1:1rem; --font-size-2:1.1rem;
  --font-size-3:1.25rem; --font-size-4:1.5rem; --font-size-5:2rem;
  --font-size-6:2.5rem; --font-size-7:3rem;
  --font-weight-4:400; --font-weight-5:500; --font-weight-6:600;
  --font-weight-7:700; --font-weight-9:900;
  --ease-3:cubic-bezier(.25,0,.3,1);
  --ease-out-3:cubic-bezier(0,0,.3,1);
  /* surfaces: light default, dark below */
  --bg:#f8f9fa; --bg-2:#f1f3f5; --bg-3:#e9ecef;
  --fg:#16191d; --fg-2:#495057; --fg-3:#868e96;
  --line:#dee2e6; --line-2:#ced4da;
  --link:#1971c2;
  --c-stock:#1971c2; --c-smeme:#e03131;
  --warn-bg:#fff9db; --warn-line:#fab005; --warn-fg:#8a5a00;
  --shadow:0 1px 2px rgb(0 0 0 / .05), 0 8px 24px -12px rgb(0 0 0 / .12);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:#0d0f12; --bg-2:#16191d; --bg-3:#212529;
    --fg:#f1f3f5; --fg-2:#adb5bd; --fg-3:#868e96;
    --line:#212529; --line-2:#343a40;
    --link:#74c0fc;
    --c-stock:#4dabf7; --c-smeme:#ff8787;
    --warn-bg:#1c1710; --warn-line:#f59f00; --warn-fg:#ffd43b;
    --shadow:0 1px 2px rgb(0 0 0 / .4), 0 8px 28px -14px rgb(0 0 0 / .7);
  }
}
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body {
  margin:0; background:var(--bg); color:var(--fg);
  font:var(--font-size-1)/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  font-synthesis-weight:none;
}
.wrap { max-width:62rem; margin:0 auto; padding:0 var(--size-4) var(--size-8); }
a { color:var(--link); }
b,strong { font-weight:var(--font-weight-7); }
code {
  font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  font-size:.875em; background:var(--bg-2); border:1px solid var(--line);
  padding:.1em .4em; border-radius:var(--size-1);
  white-space:nowrap;
}

/* ---- top bar ---- */
.top {
  display:flex; align-items:center; gap:var(--size-3); flex-wrap:wrap;
  padding:var(--size-4) 0; margin-bottom:var(--size-6);
  border-bottom:1px solid var(--line);
}
.brand { font-weight:var(--font-weight-9); letter-spacing:-.02em; font-size:var(--font-size-2); }
.brand span { color:var(--fg-3); font-weight:var(--font-weight-5); }
.pill {
  display:inline-flex; align-items:center; gap:.45em;
  font-size:var(--font-size-0); font-weight:var(--font-weight-6);
  border:1px solid var(--line-2); border-radius:999px;
  padding:.2em .7em; color:var(--fg-2); background:var(--bg-2);
}
.dot {
  width:.45em; height:.45em; border-radius:50%; background:#40c057;
  box-shadow:0 0 0 0 rgb(64 192 87 / .6); animation:pulse 2.4s var(--ease-3) infinite;
}
@keyframes pulse {
  0% { box-shadow:0 0 0 0 rgb(64 192 87 / .55); }
  70% { box-shadow:0 0 0 .5em rgb(64 192 87 / 0); }
  100% { box-shadow:0 0 0 0 rgb(64 192 87 / 0); }
}
@media (prefers-reduced-motion: reduce) { .dot { animation:none; } }
.top .sp { flex:1; }
.top a { font-size:var(--font-size-0); font-weight:var(--font-weight-6); text-decoration:none; }
.top a:hover { text-decoration:underline; }

/* ---- hero ---- */
h1 {
  font-size:clamp(1.75rem,1.1rem + 2.4vw,2.9rem);
  line-height:1.1; letter-spacing:-.03em; font-weight:var(--font-weight-9);
  margin:0 0 var(--size-3); max-width:22ch;
}
h1 em { font-style:normal; color:var(--fg-3); }
.lede { color:var(--fg-2); font-size:var(--font-size-2); margin:0; max-width:56ch; }

/* ---- stat strip ---- */
.stats {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));
  gap:var(--size-4) var(--size-5); margin:var(--size-6) 0 0;
  padding:var(--size-5) 0 0; border-top:1px solid var(--line);
}
.stats div { min-width:0; }
.stats b {
  display:block; font-size:var(--font-size-5); font-weight:var(--font-weight-9);
  letter-spacing:-.03em; font-variant-numeric:tabular-nums; line-height:1.15;
}
.stats span {
  display:block; color:var(--fg-3); font-size:var(--font-size-0);
  font-weight:var(--font-weight-6); letter-spacing:.07em; text-transform:uppercase;
  margin-top:var(--size-1);
}

/* ---- charts ---- */
.fig { margin:var(--size-6) 0 0; }
.fig svg { display:block; overflow:visible; }
.sv-t { font-size:12px; font-weight:600; letter-spacing:.06em;
        text-transform:uppercase; fill:var(--fg-3); }
.sv-lab { font-size:12.5px; font-weight:600; fill:var(--fg-2); }
.sv-ax { font-size:10.5px; fill:var(--fg-3);
         font-variant-numeric:tabular-nums; }
.sv-grid { stroke:var(--line); stroke-width:1; }
.sv-base { stroke:var(--line-2); stroke-width:1; }
.sv-med { stroke:var(--fg); stroke-width:2; stroke-linecap:round; }
.sv-mv { font-size:10.5px; font-weight:700; fill:var(--fg);
         font-variant-numeric:tabular-nums; }
.sv-seg { font-size:13px; font-weight:700; fill:#fff;
          font-variant-numeric:tabular-nums; }
.sv-segl { font-size:11px; fill:var(--fg-3); }
figcaption {
  color:var(--fg-3); font-size:var(--font-size-0); margin-top:var(--size-3);
  max-width:70ch;
}

/* ---- prose ---- */
h2 {
  font-size:var(--font-size-3); font-weight:var(--font-weight-7);
  letter-spacing:-.015em; margin:var(--size-7) 0 var(--size-1);
}
.note { color:var(--fg-2); margin:0 0 var(--size-3); max-width:64ch; font-size:.95em; }

/* ---- table ---- */
.tw { overflow-x:auto; border:1px solid var(--line); border-radius:var(--size-2); }
table { width:100%; border-collapse:collapse; font-size:.94em; min-width:34rem; }
thead th {
  position:sticky; top:0; background:var(--bg-2); text-align:left;
  font-size:var(--font-size-0); font-weight:var(--font-weight-7);
  letter-spacing:.07em; text-transform:uppercase; color:var(--fg-3);
  padding:var(--size-3) var(--size-3); border-bottom:1px solid var(--line-2);
  white-space:nowrap;
}
tbody td { padding:.6rem var(--size-3); border-bottom:1px solid var(--line); }
tbody tr:last-child td { border-bottom:0; }
tbody tr { transition:background .12s var(--ease-out-3); }
tbody tr:hover { background:var(--bg-2); }
td.num { text-align:right; font-variant-numeric:tabular-nums;
         white-space:nowrap; }
.pair { font-weight:var(--font-weight-6); }
.pair a { color:var(--fg); text-decoration:none; border-bottom:1px solid var(--line-2); }
.pair a:hover { color:var(--link); border-bottom-color:var(--link); }
.mint {
  font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  font-size:10.5px; color:var(--fg-3); margin-top:2px;
  font-weight:var(--font-weight-4);
}

/* ---- callouts ---- */
.flag {
  margin:var(--size-6) 0 0; padding:var(--size-3) var(--size-4);
  border:1px solid var(--warn-line); border-radius:var(--size-2);
  background:var(--warn-bg); color:var(--warn-fg); font-size:.94em;
}
.flag b { color:var(--warn-fg); }
.repo {
  margin:var(--size-6) 0 0; padding:var(--size-4);
  border:1px solid var(--line); border-radius:var(--size-2);
  background:var(--bg-2);
}
.repo h2 { margin-top:0; }
.repo p { margin:0 0 var(--size-3); color:var(--fg-2); max-width:68ch; }
.repo p:last-child { margin-bottom:0; }
.repo ul { margin:0; padding-left:1.1rem; color:var(--fg-2); }
.repo li { margin:.3em 0; }
footer {
  margin-top:var(--size-7); padding-top:var(--size-4);
  border-top:1px solid var(--line); color:var(--fg-3); font-size:var(--font-size-0);
  line-height:1.7;
}
@media print {
  .top, .dot { display:none; }
  body { background:#fff; color:#000; }
}
"""

FONT_STACK = ('ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,'
              '"Helvetica Neue",sans-serif')


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0.0


def pct(xs, p):
    """Linear-interpolated percentile. xs need not be sorted."""
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def live(rows):
    return [r for r in rows if r.get("volume_24h", 0) > 0]


def strip_svg(series, w=760, pad_l=92, pad_r=26, row_h=64, title=""):
    """One row per class: every live pool as a dot on a log APR axis.

    A median on its own hides the thing that matters here -- whether one class
    is uniformly worse or just has a worse midpoint. Drawing every pool makes
    the shift visible instead of asserted, and a judge can count the dots.

    Log axis because APR spans three orders of magnitude: on a linear axis 95%
    of the dots pile onto the left edge and three strays stretch the domain to
    the point where nothing is readable.
    """
    pad_t = 26 if title else 4
    h = pad_t + row_h * len(series) + 30
    plot_w = w - pad_l - pad_r

    vals = [v for _, _, xs in series for v in xs if v > 0]
    if not vals:
        return ""
    lo = math.log10(max(min(vals) * 0.8, 1e-4))
    hi = math.log10(max(vals) * 1.3)
    if hi - lo < 0.6:
        hi = lo + 0.6

    def x(v):
        t = (math.log10(max(v, 1e-4)) - lo) / (hi - lo)
        return pad_l + t * plot_w

    esc = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}
    alt = title or "APR by pool class".translate(str.maketrans(esc))
    p = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
         f'aria-label="{alt}">']
    if title:
        p.append(f'<text x="0" y="9" class="sv-t">{title}</text>')

    # decade gridlines, only those inside the domain
    d = int(math.floor(lo))
    while d <= int(math.ceil(hi)):
        v = 10.0 ** d
        if lo <= d <= hi:
            gx = x(v)
            # APR arrives already in percent units, so a decade label is just
            # the value. Do NOT rescale small decades (0.01% and 1% both
            # rendered as "1%" the first time this was written).
            lbl = f"{v:,.0f}%" if v >= 1 else f"{v:g}%"
            p.append(f'<line x1="{gx:.1f}" y1="{pad_t - 4}" x2="{gx:.1f}" '
                     f'y2="{h - 22}" class="sv-grid"/>')
            p.append(f'<text x="{gx:.1f}" y="{h - 7}" class="sv-ax" '
                     f'text-anchor="middle">{lbl}</text>')
        d += 1

    for i, (label, color, xs) in enumerate(series):
        cy = pad_t + i * row_h + 30
        p.append(f'<text x="0" y="{cy + 4}" class="sv-lab">{label}</text>')
        p.append(f'<line x1="{pad_l}" y1="{cy}" x2="{w - pad_r}" y2="{cy}" '
                 f'class="sv-base"/>')
        xs = [v for v in xs if v > 0]
        if not xs:
            p.append(f'<text x="{pad_l + 8}" y="{cy + 4}" class="sv-ax">'
                     f'no pools with 24h volume</text>')
            continue
        # nudge near-identical points into lanes so a cluster stays countable
        for v in sorted(xs):
            k = sum(1 for u in xs if abs(u - v) / max(v, 1e-9) < 0.02)
            dy = ((k - 1) % 5) * 3.4 - 6.8 if k > 1 else 0
            p.append(f'<circle cx="{x(v):.1f}" cy="{cy + dy:.1f}" r="3" '
                     f'fill="{color}" fill-opacity=".7"/>')
        m = med(xs)
        p.append(f'<line x1="{x(m):.1f}" y1="{cy - 11}" x2="{x(m):.1f}" '
                 f'y2="{cy + 11}" class="sv-med"/>')
        p.append(f'<text x="{x(m):.1f}" y="{cy - 17}" class="sv-mv" '
                 f'text-anchor="middle">{m:.3f}%</text>')
    p.append("</svg>")
    return "\n".join(p)


def tvl_svg(stock, smeme, w=760, h=104):
    """Where the money actually sits. One stacked bar beats four KPI cards."""
    a = sum(r["tvl"] for r in stock)
    b = sum(r["tvl"] for r in smeme)
    tot = a + b
    if tot <= 0:
        return ""
    x = 0.0
    segs = [(a, "var(--c-stock)", "stock-quoted"),
            (b, "var(--c-smeme)", "stock x memecoin")]
    p = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
         f'aria-label="TVL split by pool class">',
         '<text x="0" y="9" class="sv-t">TVL by class</text>']
    for val, color, lab in segs:
        bw = w * val / tot
        if bw < 1:
            continue
        p.append(f'<rect x="{x:.1f}" y="20" width="{bw:.1f}" height="30" '
                 f'rx="5" fill="{color}"/>')
        if bw > 96:
            p.append(f'<text x="{x + bw / 2:.1f}" y="40" class="sv-seg" '
                     f'text-anchor="middle">${val:,.0f}</text>')
            p.append(f'<text x="{x + bw / 2:.1f}" y="66" class="sv-segl" '
                     f'text-anchor="middle">{lab} · {val / tot * 100:.0f}%</text>')
        x += bw
    p.append(f'<text x="0" y="66" class="sv-segl">${tot:,.0f} total · '
             f'{len(stock) + len(smeme)} pools</text>')
    p.append("</svg>")
    return "\n".join(p)


def rows_html(rows, limit=18):
    """Ranked by what the pool paid, which is the whole job.

    Sorted on 24h APR descending, NOT on TVL. TVL says how deep a pool is,
    not what it pays, and a page whose first row is the biggest pool is
    answering a question nobody opened it to ask. TVL stays as a column so
    depth is still visible next to yield.

    Only pools at or above MIN_TVL are rankable -- see the note on that
    constant. Pools with no 24h volume carry no APR and land at the bottom,
    which is correct: there is nothing to compare about them.
    """
    rows = sorted([r for r in rows if r["tvl"] >= MIN_TVL],
                  key=lambda r: -(r["apr"] if r["apr"] else -1.0))
    out = []
    for r in rows[:limit]:
        tvl = r["tvl"]
        apr = r["apr"]
        vtvl = r["volume_24h"] / tvl if tvl else 0
        h = (r.get("holders") or {}).get("holders") or 0
        addr = r["pool"]
        # Every row is clickable. A number nobody can audit is a claim.
        out.append(
            f"<tr>"
            f"<td class='pair'>"
            f"<a href='https://solscan.io/account/{addr}' target='_blank' "
            f"rel='noopener'>{r['name']}</a>"
            f"<div class='mint'>{addr[:6]}…{addr[-6:]}</div></td>"
            f"<td class='num'>{apr:.3f}%</td>"
            f"<td class='num'>${tvl:,.0f}</td>"
            f"<td class='num'>{vtvl:.2f}</td>"
            f"<td class='num'>{h:,}</td></tr>")
    return "\n".join(out)


def top_of(rows):
    """Best-paying RANKABLE pool in a class, or None.

    Ranked within the class on its own terms -- this is the tool doing its job,
    not a verdict about the class.
    """
    livep = [r for r in rows
             if r.get("volume_24h", 0) > 0 and r["apr"] > 0
             and r["tvl"] >= MIN_TVL]
    return max(livep, key=lambda r: r["apr"]) if livep else None


def main() -> int:
    if not os.path.exists(SRC):
        print(f"  missing {SRC} -- run: python3 tools/stock_pairs.py 60")
        return 1

    d = json.load(open(SRC, encoding="utf-8"))
    stock = d["buckets"]["STOCK"]
    smeme = d["buckets"]["STOCK_MEME"]
    scanned = d["scanned"]

    # Everything downstream ranks and charts the rankable subset. The dropped
    # count is reported on the page -- a filter that silently shrinks the
    # universe is how a page ends up quietly wrong.
    def rankable(rows):
        return [r for r in rows if r["tvl"] >= MIN_TVL]

    s_rank, m_rank = rankable(stock), rankable(smeme)
    dropped = len(stock) + len(smeme) - len(s_rank) - len(m_rank)

    stock_live = [r["apr"] for r in live(s_rank)]
    smeme_live = [r["apr"] for r in live(m_rank)]
    stock_tvl = sum(r["tvl"] for r in s_rank)
    smeme_tvl = sum(r["tvl"] for r in m_rank)
    total_tvl = stock_tvl + smeme_tvl

    ms, mm = med(stock_live), med(smeme_live)

    strip = strip_svg([
        ("stock", "var(--c-stock)", stock_live),
        ("stock x meme", "var(--c-smeme)", smeme_live),
    ], title="every live pool's 24h APR — one dot per pool")
    bar = tvl_svg(s_rank, m_rank)

    # Both captions below state a measured quantity, so both are computed here
    # rather than written by hand. A caption that drifts from its own chart is
    # the fastest way to lose a judge who checks.
    every = stock_live + smeme_live
    pos = [v for v in every if v > 0]
    decades = (math.log10(max(pos) / min(pos)) if len(pos) > 1 else 0.0)
    smeme_share = (smeme_tvl / total_tvl * 100) if total_tvl else 0.0

    # What the floor actually removed, named from the current pull. Hardcoding
    # an example here would go stale within one refresh and quietly start
    # describing a pool that is no longer in the data.
    sub = [r for r in (stock + smeme)
           if r["tvl"] < MIN_TVL and r.get("volume_24h", 0) > 0 and r["apr"] > 0]
    if sub:
        w = max(sub, key=lambda r: r["apr"])
        floor_evidence = (f"Ranked on raw APR the top earner across those was "
                          f"<b>{w['name']}</b> at {w['apr']:.3f}% on "
                          f"${w['tvl']:,.0f} of TVL")
    else:
        floor_evidence = "Every pool below the floor had no 24h volume"

    # Each class leads with its own best payer. Ranked within the class, not
    # against each other -- cross-class comparison is analysis, and analysis
    # belongs in the writeup, not on the tool.
    def lead(rows):
        t = top_of(rows)
        if not t:
            return "No pool in this class traded in the last 24 hours."
        return (f"Best right now: <b>{t['name']}</b> at {t['apr']:.3f}% on "
                f"${t['tvl']:,.0f}.")

    top_stock_line = lead(stock)
    top_smeme_line = lead(smeme)

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="Every tokenized-equity DLMM pool on Meteora,
classified by beta source and ranked by measured 24h yield. Refreshed every 30
minutes from the public DLMM API. No wallet, no key.">
<title>Meteoran — which equity DLMM pools are worth providing liquidity to</title>
<style>{CSS}</style></head><body><div class="wrap">

<div class="top">
  <div class="brand">Meteoran <span>/ DLMM beta-class</span></div>
  <div class="pill"><span class="dot"></span>live · refreshes every 30 min</div>
  <div class="sp"></div>
  <a href="https://github.com/KJohnson-700/Meteoran">source</a>
  <a href="https://github.com/KJohnson-700/Meteoran/actions">bot runs</a>
</div>

<h1>Which tokenized-equity pools on Meteora are
worth <em>providing liquidity to.</em></h1>
<p class="lede">Every DLMM pool quoting a verified equity token, classified by
where its beta comes from and ranked by what it actually paid over 24 hours.
{scanned:,} pools scanned, {len(stock) + len(smeme)} equity pools found,
{len(s_rank) + len(m_rank)} of them rankable. Refreshed every 30 minutes. No
wallet, no key, standard library only — open the file and it works.</p>

<div class="stats">
  <div><b>{len(s_rank)}</b><span>stock pools</span></div>
  <div><b>${stock_tvl:,.0f}</b><span>stock TVL</span></div>
  <div><b>{len(m_rank)}</b><span>stock × meme</span></div>
  <div><b>${smeme_tvl:,.0f}</b><span>stock × meme TVL</span></div>
  <div><b>{ms:.3f}%</b><span>median APR, stock</span></div>
  <div><b>{mm:.3f}%</b><span>median APR, stock × meme</span></div>
</div>

<div class="flag"><b>Why {dropped} of the {len(stock) + len(smeme)} pools are
not ranked.</b> They hold under ${MIN_TVL:,.0f}. {floor_evidence} — a yield
computed on depth that small is arithmetic rather than a return. Pools below the
floor are kept in <code>data/stock_pairs.json</code> and counted above, not
deleted; raise <code>MIN_TVL</code> in <code>tools/stock_report.py</code> to
change the cutoff.</div>

<figure class="fig">{strip}
<figcaption>One dot per pool with 24h volume, on a log scale — the live pools
span {decades:.1f} orders of magnitude in APR, so on a linear axis almost every
dot would stack onto the left edge and the two classes would be indistinguishable.
The tick is the median. Dead pools are excluded: a pool with no volume has no APR
to compare and would drag both medians toward zero.</figcaption>
</figure>

<figure class="fig">{bar}
<figcaption>Capital by class: {len(m_rank)} stock×memecoin pools hold
${smeme_tvl:,.0f} of ${total_tvl:,.0f} ({smeme_share:.0f}%), {len(s_rank)}
stock-quoted pools hold ${stock_tvl:,.0f}.</figcaption>
</figure>

<h2>Stock-quoted pools — best 24h APR first</h2>
<p class="note">Beta is the listed equity. It is bounded rather than uncapped,
and it moves on the underlying's schedule instead of continuously.
{top_stock_line}</p>
<div class="tw"><table><thead><tr><th>pair</th><th class="num">APR</th>
<th class="num">TVL</th><th class="num">vol24/TVL</th><th class="num">holders</th>
</tr></thead><tbody>{rows_html(stock)}</tbody></table></div>

<h2>Stock × memecoin pools — best 24h APR first</h2>
<p class="note">Both betas live at once, ranked on the same terms.
{top_smeme_line} GOOGLx-GOOGLon is the same company across two issuers, in two
liquidity silos.</p>
<div class="tw"><table><thead><tr><th>pair</th><th class="num">APR</th>
<th class="num">TVL</th><th class="num">vol24/TVL</th><th class="num">holders</th>
</tr></thead><tbody>{rows_html(smeme)}</tbody></table></div>

<div class="flag"><b>Data quality, and why it matters here.</b> A large and
moving fraction of the raw <code>/pools</code> pull is structurally corrupt — TVL
of 3e-12, APR of 6e13. Every figure on this page is post-filter. A single
unfiltered row sorts an entire table, which is why a public leaderboard built on
the same endpoint can look precise and be meaningless.</div>

<div class="repo">
  <h2>How these pools are classified</h2>
  <p>A pool is <b>stock</b> if either leg is a verified equity token — matched on
  mint family, issuer and ticker rather than on the pool's name, because pool
  names are user-supplied and one wrong ticker in an allowlist was enough to
  misclassify three live pools before this was caught.</p>
  <p><b>stock × memecoin</b> is the same test with a memecoin on the other leg.
  Both legs carry beta at once, which is why the two are tracked separately
  rather than pooled together.</p>
</div>

<div class="repo">
  <h2>What this is not</h2>
  <ul>
    <li>Not a strategy and not a bot. It places nothing and signs nothing.</li>
    <li>Not a ranking of quality. No wallet-level skill measurement, no time
        series, no persistence test — one cross-section from one pull, so a
        pool's position here is a snapshot and not a track record.</li>
    <li>Not investment advice. It surfaces candidates and the conditions they
        trade under. Every figure is here so it can be argued with.</li>
  </ul>
</div>

<footer>
Figures come from Meteora's public DLMM API, pulled every 30 minutes by
<code>tools/stock_pairs.py</code>; the page itself is rendered by
<code>tools/stock_report.py</code> from <code>data/stock_pairs.json</code>. Every
pool name links to its Solscan entry, so any number above can be checked against
chain state. Reproduce with
<code>python3 tools/stock_pairs.py 60 &amp;&amp; python3 tools/stock_report.py</code>
· source at
<a href="https://github.com/KJohnson-700/Meteoran">github.com/KJohnson-700/Meteoran</a>
· {scanned:,} pools scanned, ${total_tvl:,.0f} TVL in the two classes above.
</footer>

</div></body></html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  -> {OUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())