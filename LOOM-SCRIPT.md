# Loom script — 4:00

Plain description of what the software does. No claims, no findings, no
comparisons. The contest asked for *"more asset classes on the same liquidity
layer"* — this shows the asset class being added and the layer working on it.

## Pre-flight — right before you record

```bash
cd meteoran
git pull
python3 tools/stock_pairs.py 60
python3 tools/stock_report.py
python3 tools/_summary.py --sync
```

Then open the live page and check these still match. If they moved, use the new
numbers:

| on screen | should read |
|---|---|
| pools scanned | `[VERIFY AT RECORD TIME]` |
| equity pools found | `[VERIFY AT RECORD TIME]` |
| rankable | `[VERIFY AT RECORD TIME]` |
| first table sorted by | 1h, highest first |

Everything else on the page is read off the screen while you talk. Don't recite
it from memory.

---

### 1 — what the contest asked for (0:00–0:30)

> "The brief asks for more asset classes on the same liquidity layer. Tokenized
> equity is already on DLMM — it's already there, nobody's tooling covers it.
> This is what I built to cover it."

**Screen:** the live page, top of it.

---

### 2 — what the bot does, part one: pull and sort (0:30–1:30)

> "It runs every thirty minutes with no API key. It pulls every DLMM pool
> Meteora publishes, then checks each pool's two tokens against a list of
> verified equity mints. It matches on the mint address, not the pool name,
> because anyone can name a pool whatever they want."

**Screen:** scroll slowly down the page.

> "Pools get split into two groups — a stock paired with SOL or USDC, and a
> stock paired with a memecoin. Then it throws out two kinds of junk. Some rows
> come back from the API with broken numbers, TVL of three times ten to the
> minus twelve. And some pools are real but tiny — under a thousand dollars —
> where the percentage looks huge and means nothing. Both are dropped, and the
> page tells you how many."

**Screen:** the yellow floor flag. Point at it.

---

### 3 — what the bot does, part two: rank (1:30–2:30)

> "Then it ranks. What it ranks on is what the pool actually paid — and it
> shows that over six different time windows: thirty minutes, one hour, two,
> four, twelve, and twenty-four. Every column header is a sort button, so if
> you want the last thirty minutes you click thirty minutes."

**Screen:** the stock table. Click the `24h` header, then click `30m`. Let it
re-sort.

> "It defaults to one hour. A twenty-four hour number is an average over a day
> the pool might have been sitting idle for most of — a pool can print its
> whole day in one busy hour and then stop, and on a twenty-four hour view that
> looks the same as one that traded steadily. One hour is recent enough to
> matter and long enough not to be one trade."

**Screen:** the `Why one window is not enough` flag. Point at it.

---

### 4 — the second half of the tool: the alerter (2:30–3:20)

> "That's the report. It's the same codebase as a second thing — an alerter.
> The report runs every thirty minutes and produces a page. The alerter runs
> continuously, checks each pool against nine gates, and pushes to a phone only
> when all nine pass. Same gates, different clock, because a gate reads
> Meteora's rolling half-hour, hour, twelve-hour and day windows."

**Screen:** terminal, `python3 tools/pool_alert.py` output, or the section in
the README on the nine gates.

> "The alert is filtered by group too, so you can watch just the stock pairs,
> or just the stock-and-memecoin ones."

**Screen:** the pool_alert section.

---

### 5 — how it runs, and how to check it (3:20–4:00)

> "Neither of those needs a wallet or a key. Nothing signs anything. The
> report is one HTML file — you open it, there's no server and nothing to
> install. The refresh is a scheduled GitHub Action, so the page is live and the
> runs are public."

**Screen:** `bot runs` in the top bar, then the terminal.

> "And the whole thing regenerates from two commands, standard library only."

**Screen:** terminal, `python3 tools/stock_pairs.py 60`

> "That's it. It covers every DLMM pool on Meteora that quotes a verified
> equity token, tells you which ones actually paid and which ones didn't, and
> lets you watch the ones worth watching. Thanks."

**Screen:** repo URL.

---

## Don'ts

- **Don't state a comparison between the two groups as a finding.** Median
  ratios, "Nx worse", "pays less" — none of that. It's a cross-section from one
  pull; the numbers move every thirty minutes and a ratio can be undefined when
  the denominator is zero. The page deliberately makes no claim, so don't make
  one on camera either.
- Don't say "APR." Meteora's `apr` field is a 24-hour fee/TVL percentage with no
  annualisation. The page says "yield" for that reason.
- Don't promise a strategy or imply it places anything. It reads and reports.
- Don't claim impermanent loss, returns, or anything predictive.
- Don't quote a percentage of "corrupt" API rows — it moves between pulls. Say
  "a large, moving share" and point at the flag.

## If a judge asks

**"Is this validated / is it an edge?"** — No. It's a pool-level cross-section
from one pull. No time series, no wallet-level skill measurement, not built.

**"Why not just use the API?"** — You can. The API returns 24,000 pools with a
large share of corrupt rows, and no field telling you which pool is an equity
pair. That's the classification and the filtering, and it's all in the repo.

**"Where's the session-boundary study?"** — Not built. The OHLCV endpoint caps
at ten candles per call, so it can't be done from one pull. Recorded as not
built, not estimated.

**"Was this already submitted to Colosseum?"** — **Answer before you record.**
That field is on the form and the answer isn't known yet.