# Submission — Meteora DBC track

Copy from here into the form. The paragraph marked `live-figures` is generated,
not written — run `python3 tools/_summary.py --sync` immediately before you paste
so the numbers match the page you are recording, then check
`kjohnson-700.github.io/Meteoran/stock-pairs.html`.

---

## Project Name

Meteoran

## Project Description

DLMM liquidity tooling, extended to tokenized equity.

Meteoran's gates were calibrated on memecoin DLMM across 111,838 closed positions. The headline result is that impermanent loss isn't the risk — token beta is. Fee capture scales monotonically with outcome, and fees covered IL 3.74x. Which means the gates can't be assumed to carry over to a new asset class without testing them.

<!-- live-figures:begin -->
Nobody has run that test on tokenized equity. Of 24,000 DLMM pools scanned, 37 hold at least $1,000 and quote an equity token: 23 stock-quoted, 14 pairing a stock against a memecoin. Ranked on the same rolling windows the gates read rather than a 24-hour average — a pool that paid its whole day in one busy hour and has been idle since looks identical, on a 24h view, to one that traded steadily. On pools that actually traded, median 1h yield is 0.0079% for stock-quoted pools (n=23) and 0.0000% for stock×memecoin (n=14). The median stock×memecoin pool earned nothing at all over 1h, against 0.0079% for the median stock-quoted pool — so there is no ratio to quote, only a difference between a market that trades and one that does not. The equity leg is the same either way, so the entire difference is the other leg.
<!-- live-figures:end -->

tools/stock_pairs.py classifies every pool by beta source and ranks it. pool_alert.py tags alerts by class, so you can scan equity pairs only and get a phone push with the pool link instead of watching a browser.

Two cadences, two objects. The report is a map — batch scan, refreshed every 30 minutes by a GitHub Action, for reading. The alerter is an alarm — continuous, operator-tunable, pushes only when all nine gates pass. Binding a signal to a document's refresh rate would be the bug. And the 20-minute alert default isn't arbitrary: the gates read Meteora's rolling 30m/1h/12h/24h windows, so 30 minutes is the freshest input available. Polling every 5 minutes samples that window six times and learns nothing; polling every 30 aliases, sampling the same phase each cycle and walking past the peak. Twenty puts two samples inside every window, at different phases.

Two things I'd rather flag than bury. The OHLCV endpoint caps at 10 candles per call, so the session-boundary study — do equity pools widen when the underlying reopens — isn't testable from one pull. It's recorded as not built, not estimated. And I found a bug mid-build: a ticker I'd added to the equity allowlist from memory turned out to be a memecoin, and it was misclassifying three live pools. Regression test is in the repo.

Read-only, standard library only, no keys. Public DLMM API.

## Project Github Link

https://github.com/KJohnson-700/Meteoran

## Project Website

https://kjohnson-700.github.io/Meteoran/stock-pairs.html

Fallback if that ever breaks:
https://raw.githubusercontent.com/KJohnson-700/Meteoran/main/docs/stock-pairs.html

## Link to pitch deck or Loom

<your Loom link here — record with Win + Alt + R against the live report>

---

## If they ask "is this running?"

Answer straight: **the code is, the measurement reproduces in two commands, the
instance is not hosted.** That's the honest framing and it's the whole thesis —
this is a method you run, not a service you log into. The report *is* live and
refreshes on its own; the phone alerter runs on the operator's machine because a
push channel that anyone else could subscribe to would be a different (and
worse) product.

## Numbers to re-verify before submitting

The 30-minute workflow means these drift, which is why the description above is
generated rather than hand-written. Run this once, immediately before you paste:

```bash
python3 tools/_summary.py --sync
```

It rewrites the `live-figures` paragraph from `data/stock_pairs.json` — the same
file the page is rendered from — so the copy you paste and the page you record
cannot disagree. If the live page still differs from what `--sync` just wrote,
pull first and re-run:

```bash
python3 tools/stock_pairs.py 60 && python3 tools/stock_report.py && python3 tools/_summary.py --sync
```
```