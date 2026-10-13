# Loom script — 4:00 target

**Rewritten for the multi-window page.** The previous version ranked and narrated
this page as if 24h were the only number, and it recited a "11x" ratio that is
**undefined on the current pull**. Both are gone. The page now carries five
sortable windows and ranks on 1h; every figure below was read off the current
render.

Record at 1080p. **Figures drift every 30 minutes** — run the pre-flight
immediately before you press record. Wherever the script marks `[ON SCREEN]`,
read the number off the screen instead of reciting it. There is exactly one
spoken figure, in Shot 4, because that is the claim.

---

## Before you record — two things only you can answer

1. **"Already submitted to Colosseum?"** is a field on the submission form and I
   don't know the answer. Answer it before you record, not during.
2. Re-run the pre-flight below and read the `ratio` line it tells you to read.

---

## Pre-flight — immediately before recording

```bash
cd meteoran
git pull
python3 tools/stock_pairs.py 60
python3 tools/stock_report.py
python3 tools/_summary.py --sync
```

`--sync` rewrites the figures inside `SUBMISSION.md` from the same JSON the page
renders from, so what the form says and what the screen shows cannot disagree.

Then read the `ratio` line that `_summary.py` prints. **It decides what you are
allowed to say in Shot 4:**

- `ratio undefined (denominator median is 0)` — this is what it printed on the
  last verified pull. The stock×memecoin median is **exactly zero**, so there is
  no ratio to state. Say the dormancy line. Do not say a multiple.
- a number like `12.7x` — both medians were above zero this time. You may say
  the multiple. Still read the two medians off the screen, don't recite them.

Then confirm these on screen before you start:

| what | last verified | check |
| --- | --- | --- |
| lede | "85 equity pools found, 37 of them rankable" | `[VERIFY AT RECORD TIME]` |
| floor flag | "Why 48 of the 85 pools are not ranked" | `[VERIFY AT RECORD TIME]` |
| default sort | both tables sorted on **1h**, not 24h and not TVL | `[VERIFY AT RECORD TIME]` |
| headers | five clickable: 30m, 1h, 4h, 12h, 24h | `[VERIFY AT RECORD TIME]` |
| stats | 23 stock pools / 14 stock×meme pools | `[VERIFY AT RECORD TIME]` |

If any of those changed shape, re-read the numbers off the screen rather than
rehearsing this script.

---

### Shot 1 — what it is (0:00–0:30)

> "Meteoran measures Meteora DLMM liquidity. Read-only, no keys, standard library
> only. This page is the part that didn't exist before: which tokenized-equity
> pools are worth putting liquidity into right now."

**Screen:** live page, top. Let the headline and the stat tiles sit.

---

### Shot 2 — the universe, and the part that surprised us (0:30–1:10)

> "It scans twenty-four thousand DLMM pools and finds eighty-five that quote a
> verified equity token. Then it ranks them — and here's what I didn't expect.
> Sixty-two of those eighty-five hold under five thousand dollars. The median pool
> holds six hundred and nineteen."

**Screen:** scroll to the stat tiles, then to the floor flag.

> "So there's a floor at a thousand dollars of TVL. Without it, the top earner
> on this whole page is a pool with no meaningful depth in it, printing a yield
> in the five figures. That's arithmetic, not a return. Thirty-seven pools survive
> the floor, and the page tells you exactly how many it dropped and why."

**Screen:** the floor flag. `[ON SCREEN]` — point at the pool name and its TVL
it names. **Do not recite either.** That line is recomputed from the pull and it
will be a different pool by tonight.

---

### Shot 3 — the tool doing its job, across windows (1:10–2:00)

> "Each table has five windows — thirty minutes, one hour, four, twelve, twenty-four
> — and every one of them is a sort header. It ranks on one hour by default,
> because that's what's paying now, but I didn't want to pick for you."

**Screen:** stock table. **Click the 24h header, then click the 1h header.** Let
the row order visibly change. `[ON SCREEN]` — do not recite any cell.

> "This matters more than it sounds. Ranking on a 24-hour figure is a category
> error — it's an average over a day in which the pool may have been idle for
> most of it."

**Screen:** the "Why one window is not enough" flag. `[ON SCREEN]` — it names a
real pool from the current pull and prints both its windows. Let it speak.

> "That's a pool that paid well over the day and had almost nothing left by the
> end of it. A 24-hour-only ranking still calls it the best payer."

**Screen:** back to the stock×meme table. Point at the first row.

> "Every pool name links to Solscan. Any number on this page can be checked
> against chain state."

**Screen:** click one row, let Solscan load, come back.

---

### Shot 4 — the finding (2:00–2:55)

> "Here's what I actually came here to find out. Meteoran's existing gates were
> calibrated on memecoin DLMM across a hundred and eleven thousand closed
> positions, and that work concluded impermanent loss is not the risk — token
> beta is. So every gate was tuned against a market that moves continuously and
> without a schedule."

> "Tokenized equity does neither. It's bounded, and it moves on the underlying's
> schedule. Nobody had tested whether the gates transfer. I did, on this pull."

**Screen:** the dot-strip chart, both rows visible at once. `[ON SCREEN]` — point
at the lower row and count the dots stacked against the axis.

> "The stock-quoted pools are paying something right now — the median one is up
> on the hour. The stock×memecoin pools mostly aren't. Eight of the fourteen
> didn't earn a fee in the last hour at all. Not less than the others. Nothing."

> "That's the finding, and it's the more useful one. The obvious reading of this
> page is 'pairing a stock with a memecoin pays less.' The honest reading is that
> these pools are largely dormant. Over a full day they do pay — but that number
> is an average across a day most of them spent idle, which is exactly the
> mistake the multi-window view exists to stop you making."

> "Same equity beta on one leg either way. The question isn't which pays less.
> It's why there's so little being traded to pay out in the first place. I don't
> have that answer yet."

**Screen:** the stat tiles — the two median cells side by side. `[ON SCREEN]` —
read the medians off the screen if you want to; do not quote a multiple out
loud. See the Don'ts below.

---

### Shot 5 — the part that isn't on the page (2:55–3:25)

> "Two things worth knowing that the tool doesn't editorialize. First, it
> classifies by mint and issuer, not by pool name — because pool names are
> user-supplied, and one ticker I'd added to the allowlist from memory turned
> out to be a memecoin and was misclassifying three live pools. There's a
> regression test for it now."

**Screen:** "How these pools are classified".

> "Second: a large and moving share of the raw API pull is structurally corrupt
> — TVL of three times ten to the minus twelve, yields of sixty trillion. Every
> figure on this page is post-filter. A single unfiltered row sorts an entire
> table, which is why a public leaderboard built on the same endpoint can look
> precise and be meaningless."

**Screen:** the data-quality flag.

---

### Shot 6 — reproduce it (3:25–3:50)

> "This isn't a snapshot. A GitHub Action re-pulls and re-renders every thirty
> minutes with no secrets, and the runs are public."

**Screen:** "bot runs" in the top bar.

> "And it regenerates from one command, standard library, no API key."

**Screen:** terminal, `python3 tools/stock_pairs.py 60`

---

### Shot 7 — close (3:50–4:00)

> "I didn't build another LP leaderboard. I tested whether a model measured on
> one asset class survives contact with another, and found where it breaks.
> That's on the page, and it's one command to check."

**Screen:** repo URL, then the live page.

---

## Don'ts

- **Never state a ratio between the two classes unless `_summary.py` printed a
  number on its `ratio` line.** When the stock×memecoin median is zero the
  quantity is undefined — dividing by it prints a confident number for something
  that isn't one. This was the single biggest error in the previous version of
  this script. Say the dormancy line instead.
- **Don't say "24h APR" as the ranking metric.** The page ranks on 1h and shows
  five windows. 24h is one column among five, not the number.
- **Don't recite the floor-flag example.** It is recomputed every pull and will
  name a different pool. Point at it.
- Don't quote a corruption percentage. Give the mechanism — 3e-12 TVL, 6e13
  yield — and let the page carry "a large and moving fraction."
- Don't claim impermanent loss or a strategy. This is a measurement.
- Don't claim wallet-level skill on equity pools. Not built — no time series, no
  persistence test. It's a cross-section from one pull.
- Don't overclaim the dormancy result either. "Most of these pools didn't trade
  in the last hour" is what you measured. "These pools are illiquid" or "these
  pools are dead" is a bigger claim than one pull supports.

## The honest line to keep

If asked *"have you validated this is an edge?"* — **No.** Pool-level
cross-section, one pull, small sample per class — 23 stock-quoted and 14
stock×memecoin at the last pull. It's a first measurement with a direction, not
a strategy. The value is that it's reproducible in one command, nobody else has
looked, and the tool ranks rather than tells you what to do.

## Known limits — in case a judge reads the page

The page says all of these itself, in "What this is not": not a bot, places
nothing, signs nothing; not a ranking of quality; not investment advice.

If asked about the missing **session-boundary study** — it is **not built**, not
estimated. The OHLCV endpoint caps at ten candles per call, so a
session-boundary measure cannot be built on this endpoint as it stands. Say that
plainly if asked; do not let it drift into sounding estimated.

If asked *"was this already submitted to Colosseum?"* — **answer before you
record.** That field is on the form and I don't know the answer.