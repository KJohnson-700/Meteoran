# Loom script — 4:00 target

Record at 1080p. Voiceover + screen. **Run `python3 tools/stock_pairs.py 60` first and
leave the terminal on the result table** — shots 3 and 4 are that output.

---

### Shot 1 — what Meteoran already is (0:00–0:40)

> "Meteoran measures Meteora DLMM liquidity. Read-only, no keys. The gates were
> calibrated on memecoins across a hundred and eleven thousand closed positions. Fee capture
> determines outcome, monotonically. Fees cover impermanent loss three point seven four
> times over."

**Screen:** repo README, the findings table. Scroll slowly.

---

### Shot 2 — the line that matters (0:40–1:00)

> "But look at the last clause of that finding. Impermanent loss is not the enemy — token
> beta is what kills positions. Which means the gates can't move to a new asset class until
> somebody tests whether they transfer. Nobody has run that test on tokenized equity."

**Screen:** README, the "impermanent loss is not the enemy" row. Highlight the last line.

---

### Shot 3 — the universe is real (1:00–1:30)

> "Tokenized equity is already on DLMM. Forty-five stock-quoted pools, over half a million
> dollars of TVL. Thirty-four more pairing a stock against a memecoin. That's a hundred and
> forty thousand in liquidity that every LP tool on Meteora is currently ignoring, because
> they all rank memecoins."

**Screen:** terminal, the STOCK table.

---

### Shot 4 — the result (1:30–2:20)

> "Rank only the pools that actually traded, and the beta class becomes the variable.
> Memecoins pay a median of zero point one two nine percent. Stocks pay zero point one one
> three — basically the same. But meme-paired-with-stock pays zero point zero two zero
> percent. Six times worse than either leg alone. Two correlated betas on one pool, and the
> fees don't cover the variance."

**Screen:** terminal, the BETA-CLASS SPREAD block. Let it sit.

---

### Shot 5 — the thing you can't see anywhere (2:20–2:55)

> "Three findings nobody else has surfaced. There's a pool right here — GOOGLx against
> GOOGLon. That's Google, issued by two different issuers, sitting in two separate
> liquidity silos. Same company, same price, no arbitrage between them. And STONK-NVDAx is
> already live: meme paired with stock. It's in the bottom decile by yield."

**Screen:** terminal, STOCK_MEME table. Point at the two rows.

---

### Shot 6 — the data is 75% garbage (2:55–3:20)

> "One more thing. Seventy-five percent of the raw pool pull is corrupt — TVL of three times
> ten to the minus twelve, APR of sixty trillion percent. That's not a bug I invented. It's
> in our own rules file from before this contest. Any tool that doesn't filter this will
> rank a garbage row to the top, and that's exactly why every public leaderboard is
> untrustworthy."

**Screen:** terminal, the "dropped N corrupt rows" line.

---

### Shot 7 — where DBC fits (3:20–3:50)

> "DBC launches graduate into DAMM v2. And Meteora's migration keepers already auto-migrate
> stock-quoted configs at a seven-fifty-dollar threshold. So stock liquidity keeps arriving
> whether anyone chose it or not — and every one of those pools lands with no position
> history, which is the single variable the whole model depends on. This is the question the
> whole stack needs answered."

**Screen:** DBC-PITCH.md section 6.

---

### Shot 8 — close (3:50–4:00)

> "We didn't build another LP ranking. We tested whether a model measured on one asset class
> survives contact with another — and found the boundary. Everything here regenerates from
> one command."

**Screen:** repo URL + `python3 tools/stock_pairs.py 60` on screen.

---

## Don'ts

- Don't say "guaranteed returns" or imply this is a strategy. It isn't — it's a measurement.
- Don't oversell the sample. 42 live stock pools is small and the pitch says so.
- Don't claim wallet-level skill on equity pools. Not built.

## The honest line to keep

If asked *"have you validated this is an edge?"* — **No.** Pool-level cross-section, one
pull, no time series. It's a first measurement with a direction, not a strategy. The value
is that it's reproducible in one command and nobody else has looked.

---

## Pre-flight

```bash
cd meteoran
python3 tools/stock_pairs.py 60
```

Take that run at full screen. Everything in shots 3–6 comes from it. Numbers move between
runs; re-record if the table shifts materially.