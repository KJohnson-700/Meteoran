# Meteoran — extending DLMM gating to tokenized equity

**Meteora DBC track · $20,000 · github.com/KJohnson-700/Meteoran**

---

## 1 — What Meteoran already is

Measurement tooling for **Meteora DLMM** liquidity. Read-only, no keys, no execution.

The gates were calibrated on one asset class — memecoins — across **111,838 closed
positions**:

> Fee capture determines outcome, **monotonically**. <0.5% fee yield → +0.0% median /
> 52% win · >25% → **+29.4% / 83% win**
>
> Impermanent loss is not the enemy. Fees **+5.99%** vs IL **−1.60%** — fees cover IL
> **3.74x**. **Token beta is what kills positions.**

That last clause is the whole project. The risk model is not "IL", it is *what the beta
is*. Which means the gates cannot transfer to a new asset class until you test whether
they do.

**Nobody has run this test on tokenized equity.**

---

## 2 — The question

Meteora's brief asks for *"more asset classes on the same liquidity layer."* DLMM already
hosts them:

| | |
|---|---|
| **45** | stock-quoted DLMM pools, **$503,391 TVL** |
| **34** | stock × memecoin pools, **$143,171 TVL** |
| **137,911** | total DLMM pools |

xStocks holds ~97% of tokenized-stock market volume, $350M+ TVL, 1:1 backed by Backed
Finance. On-chain it is just an SPL token — so it pools with everything else, and nobody
has checked whether DLMM LPs should be in it.

**Two betas, two regimes.** A memecoin's beta arrives continuously and can go to zero. An
equity's beta is bounded at ±~10%/day, and arrives **in a gap at the 9:30 open** while the
pool traded stale all night. That failure mode does not exist in the calibration set.

---

## 3 — The result

`tools/stock_pairs.py` classifies every pool by beta source and ranks only pools that
actually traded.

> **SUPERSEDED — do not quote this section.** The table below is a 24-hour median
> taken before the tool was moved off 24h-only ranking, and it is no longer what
> the tool reports. It is kept only to show the method. Current figures are
> generated: run `python3 tools/_summary.py`. The live copy in `SUBMISSION.md`
> is the only version to paste.

Historical 24h medians, superseded:

| class | median 24h APR | n |
|---|---|---|
| memecoin | **0.129%** | 2,117 |
| stock | **0.113%** | 42 |
| **stock × memecoin** | **0.020%** | 31 |

On the 24h median this looked like "the worst class by roughly 6x". **That ratio
does not survive the current ranking.** On the 1h window the median stock×memecoin
pool is frequently *exactly zero*, which makes the ratio undefined rather than
large — there is no number to quote. Do not restate a multiple between these two
classes.

The top of the live book, all measured:

```
NVDAx-SOL     126,334  1.084%   vol/TVL 6.03   174,802 holders
PLTRx-SOL      64,575  0.436%            0.80     9,303
GOOGLx-SOL     62,862  0.606%            3.53    56,839
SPYx-SOL       48,111  0.296%            1.30    79,399
METAx-USDC     23,791  1.114%           11.84    39,038
TSLAx-SOL       9,965  0.283%            1.55    47,268
STONK-NVDAx     1,734  0.245%            0.27   174,794   <- meme x stock
```

---

## 4 — What else turned up

- **Cross-issuer pools already exist.** `GOOGLx-GOOGLon` pools the same company across two
  issuers. Three issuer forms of one stock, three liquidity silos — the canonical thin-RWA
  fragmentation problem, now measurable.
- **`STONK-NVDAx` is live.** Meme-paired-with-stock already ships on DLMM. It is in the
  bottom decile by yield.
- **A large and unstable share of the raw `/pools` pull is corrupt** — `tvl = 3e-12`,
  `apr = 6e13`. Observed between **31.8% and 75.1%** across pulls, and that spread is itself
  the finding: the scan sorts by `fee_tvl_ratio_24h:desc`, so rows with absurd ratios land at
  the very top of the list. The corruption concentrates in exactly the rows a naive fee/TVL
  ranking would promote. This is why every number here is post-filter, and why the
  repository's own pre-existing notes already put 41% corrupt rows on the Meteora P&L API.

---

## 5 — What this is not

Not a strategy, not a bot, not a ranking product. Those are all broken and CLAUDE.md says
why — 41% corrupt rows, survivorship, no confidence intervals, Nansen labelling a 30-day
top-performers sort "Smart Trader".

This is the project's actual method applied to the asset class it had not touched:

1. classify the universe by beta source
2. drop what the API got wrong
3. compare classes on the same pull, live pools only
4. **let the number decide whether the gates transfer**

---

## 6 — Where DBC fits

A DBC launch **graduates into DAMM v2** — and Meteora's migration keepers already
auto-migrate stock-quoted configs at a **$750 equivalent threshold**. So stock liquidity is
arriving programmatically, not because someone chose it.

Every one of those graduating pools lands in a market with:
- no position history (the single variable the 111k-position model depends on)
- a bounded, gappy beta that arrives without warning
- and LPs who have been told nothing

**Meteoran answers one question for the whole stack: is this pool worth providing liquidity
to — and if the beta is an equity, does the same model still hold?**

---

## 7 — Evidence

```
tools/stock_pairs.py        beta classification + ranking, live API
tools/stock_report.py       static HTML export
docs/stock-pairs.html       the result, opens in any browser
data/stock_pairs.json       79 classified pools, full metrics
```

**Just open [`docs/stock-pairs.html`](https://github.com/KJohnson-700/Meteoran/blob/main/docs/stock-pairs.html).**
No wallet, no Python, no server — one self-contained file.

Reproduce from scratch:

```bash
python3 tools/stock_pairs.py 60     # 24,000 pools -> data/stock_pairs.json
python3 tools/stock_report.py       # -> docs/stock-pairs.html
```

24,000 pools pulled · a large fraction dropped as corrupt (varies by pull, see above) · 79
classified · every figure above
regenerates from those two commands.

### Notifications

Already wired, no account needed. `tools/notify.example.py` → ntfy.sh. Copy it to
`notify.py`, set an unguessable `TOPIC`, subscribe in the phone app, POST to it. The
real `notify.py` is gitignored because the topic is a shared secret — anyone holding
the string can read *and* post.

```bash
cp tools/notify.example.py tools/notify.py    # then set TOPIC
```

### The report and the alerter are different objects, on purpose

They are not two views of one thing, and they deliberately do not share a cadence.

**The report is a map.** Batch scan, renders state, you read it. Refreshed every 30
minutes by `.github/workflows/refresh.yml` because a human is the consumer and 30
minutes is fine for a document you look at twice a day.

**The alerter is an alarm.** Continuous loop, fires a phone push **only** when all nine
measured gates pass, and the interval is the operator's choice:

```bash
python3 tools/pool_alert.py 20 8 20000 stock   # every 20min, equity-quoted only
```

Tying an alarm to a document's refresh rate would be the bug. The one is a signal, the
other is a reference.

**Why the default is 20 minutes and not 5, or 30.** The gates read Meteora's rolling
`30m`, `1h`, `12h` and `24h` windows. The freshest input is the 30-minute window, so
polling at 5 minutes samples that same window six times per cycle and learns nothing —
just six times the API load. Polling at *exactly* 30 is worse: it aliases, sampling the
window at the same phase every cycle, which can walk straight past the peak.

Twenty minutes puts **two samples inside every 30-minute window**, at different phases.
That is what the number is for. It is not a round number someone picked.

| | report | alerter |
|---|---|---|
| object | map | alarm |
| fires | never, just renders | only when 9 gates pass |
| cadence | 30 min batch | 20 min default, operator-set |
| consumer | a person reading | a phone in a pocket |

### Live dashboard

`python3 tools/dashboard.py` serves a real browser board on `localhost:8787`, polling
every 15s, with `IN RANGE / ABOVE RANGE / BELOW FLOOR` states. Scoped to the operator's
own open positions, so it needs `data/operator_wallet.txt` — which is gitignored, along
with `reports/`. That is why the public result lives in `docs/` instead.

---

## 8 — Honest limits

- **Pool-level, not wallet-level.** The API requires `user` on every endpoint and cannot
  enumerate wallets, so this measures pools. Wallet skill vetting on equity pools is the
  next step and is not built.
- **One pull, not a time series.** These are cross-sections at a point in time. No
  persistence test (T2 in THESIS.md) has been run on equity pools. This is a first
  measurement, not a validated edge.
- **Mint matching is family + symbol.** xStocks mints start `Xs`, Ondo mints end `ondo`,
  cross-checked against a ticker allowlist. Anyone can mint a token called `TSLAx`; the
  mint address is the authority, and one false positive (`KOx`) was rejected this way.