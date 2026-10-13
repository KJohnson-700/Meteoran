# Loom script — 4:00 target

**This replaces the previous version entirely.** That one cited a "75% corrupt"
figure (which swings 31.8–75.1% run to run), quoted pool counts from before the
TVL floor existed, and said `STONK-NVDAx` was "bottom decile by yield" — it is
currently the *top* stock×memecoin earner on the page. Every number below is
pulled from the current render.

Record at 1080p. **Numbers drift every 30 minutes** — run the pre-flight before
you press record, and read figures off the screen rather than reciting them
wherever the script marks `[ON SCREEN]`. The only number you say out loud is the
ratio in Shot 4, because that is the claim.

---

## Pre-flight — do this immediately before recording

```bash
cd meteoran
git pull
python3 tools/stock_pairs.py 60
python3 tools/stock_report.py
python3 tools/_summary.py --sync
```

`--sync` rewrites the figures inside `SUBMISSION.md` from the same JSON the page
is rendered from, so what you say and what the screen shows cannot disagree.

Then confirm these four are still true on screen before you start:

- lede says **100 equity pools found, 40 of them rankable**
- floor flag says **Why 60 of the 100 pools are not ranked**
- stock table first row is the **highest-APR** row, not the biggest
- stock×meme table first row likewise

If any of those changed shape, re-read the numbers off the screen rather than
rehearsing this script.

---

### Shot 1 — what it is (0:00–0:30)

> "Meteoran measures Meteora DLMM liquidity. Read-only, no keys, standard library
> only. This page is the part that didn't exist before: which tokenized-equity
> pools are worth putting liquidity into right now."

**Screen:** live page, top. Let the headline and the six stat tiles sit.

---

### Shot 2 — the universe, and the part that surprised us (0:30–1:15)

> "It scans twenty-four thousand DLMM pools and finds a hundred that quote a
> verified equity token. Then it ranks them — and here's what I didn't expect.
> Seventy-seven of those hundred hold under five thousand dollars. The median
> pool holds four hundred and ninety-three."

**Screen:** scroll to the stat tiles, then to the floor flag.

> "So there's a floor at a thousand dollars of TVL. Without it, the top earner
> on this whole page is a pool with nineteen dollars in it printing two hundred
> and twenty-one percent. That's arithmetic, not a return. Forty pools survive
> the floor, and the page tells you exactly how many it dropped and why."

**Screen:** the floor flag. `[ON SCREEN]` — point at the pool name it names.

---

### Shot 3 — the tool doing its job (1:15–2:00)

> "Here's the stock-quoted class, ranked by what each pool actually paid over
> twenty-four hours."

**Screen:** stock table. Hover/point at the first two rows. `[ON SCREEN]` — do
not recite. Let the sort order speak for itself.

> "And the same ranking for stock paired against a memecoin."

**Screen:** stock×meme table. Point at the first row.

> "Every pool name links to Solscan. Any number on this page can be checked
> against chain state."

**Screen:** click one row, let Solscan load, come back.

---

### Shot 4 — the finding (2:00–2:50)

> "Here's what I actually came here to find out. Meteoran's existing gates were
> calibrated on memecoin DLMM across a hundred and eleven thousand closed
> positions, and that work concluded impermanent loss is not the risk — token
> beta is. So every gate was tuned against a market that moves continuously and
> without a schedule."

> "Tokenized equity does neither. It's bounded, and it moves on the underlying's
> schedule. Nobody had tested whether the gates transfer. I did, on this pull:
> across the pools that actually traded, median APR runs about eleven times
> lower when a stock is paired with a memecoin. Same equity beta either way, so
> the entire difference is the other leg."

**Screen:** the dot-strip chart, both rows visible at once. `[ON SCREEN]` — the
leftward shift is the evidence. Point at it; do not state the medians.

---

### Shot 5 — the part that isn't on the page (2:50–3:20)

> "Two things worth knowing that the tool doesn't editorialize. First, it
> classifies by mint and issuer, not by pool name — because pool names are
> user-supplied, and one ticker I'd added to the allowlist from memory turned
> out to be a memecoin and was misclassifying three live pools. There's a
> regression test for it now."

**Screen:** "How these pools are classified".

> "Second: a large and moving share of the raw API pull is structurally
> corrupt — TVL of three times ten to the minus twelve, APR of sixty trillion.
> The exact share moves between pulls, which is why I quote the range and not a
> number. Any tool that doesn't filter this ranks a garbage row to the top."

**Screen:** the data-quality flag.

---

### Shot 6 — reproduce it (3:20–3:50)

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

- **Don't say "11x" if the pre-flight numbers moved.** Re-read it from
  `_summary.py` or soften to "an order of magnitude". The sample is small —
  24 live stock-quoted pools and 14 stock×memecoin at last pull — and the
  script shouldn't outrun it.
- Don't claim impermanent loss or a strategy. This is a measurement.
- Don't claim wallet-level skill on equity pools. Not built — no time series,
  no persistence test. It's a cross-section from one pull.
- Don't quote a corruption percentage. Give the range and the cause.

## The honest line to keep

If asked *"have you validated this is an edge?"* — **No.** Pool-level
cross-section, one pull, small sample per class. It's a first measurement with a
direction, not a strategy. The value is that it's reproducible in one command,
nobody else has looked, and the tool ranks rather than tells you what to do.

## Known limits — in case a judge reads the page

The page says all of these itself, in "What this is not": not a bot, places
nothing, signs nothing; not a ranking of quality; not investment advice. If
asked about the missing session-boundary study — the OHLCV endpoint caps at ten
candles per call, so it's recorded as **not built**, not estimated.

If asked *"was this already submitted to Colosseum?"* — **answer before you
record.** That field is on the form and I don't know the answer.