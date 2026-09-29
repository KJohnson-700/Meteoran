# Meteoran — thesis

Started 2026-09-10, after six months on Polymarket crypto up/down produced **zero
strategies that cleared their own bar**. That project is `~/Documents/Oracle-3` and it
stays separate: different venue, different instrument, different failure modes. Nothing
carries over except the measurement discipline, which is the only thing there that
worked.

## 1. What this is

Provide liquidity on **Meteora DLMM** (Solana), by mirroring wallets that are measurably
good at it rather than by picking pools ourselves. Execution is `Valhalla` from SOL
Decoder — an NFT-gated copy-trading bot the operator already owns, so execution costs
nothing marginal and is not where any edge lives.

**The whole project is a selection problem.** The bot copies faithfully; the outcome is
entirely determined by who it copies.

## 2. The mechanism, and why it is not free money

A DLMM position is **short gamma**. You choose a price range; you earn swap fees only
while price is INSIDE it. A bid-side range (the meta the profitable wallets run) means:

    price rises away   ->  zero fees, principal intact
    price falls through ->  fees earned, and you now hold a depreciated token

**You are paid to catch falling knives, and paid nothing when they rise.** Modelled on
one $33 position in a -50%..-95% band:

| what price does | in range | fees | principal | net |
|---|---|---|---|---|
| rips up, never returns | NO | 0.00 | 33.00 | 0.00 |
| chops inside the band | yes | 3.30 | 30.00 | +0.30 |
| falls to -50% | yes | 2.40 | 24.75 | -5.85 |
| falls to -80% | yes | 3.30 | 11.00 | -18.70 |
| rug -99% | yes | 1.00 | 0.63 | -31.37 |

Break-even is not the fee rate. It is the ratio of chop-cases to -80% cases, and it
needs to be roughly **6:1**.

## 3. What the top LPs actually earn — measured, not claimed

Three human LPs (bot-filtered, see CLAUDE.md), full position history from Meteora's own
API:

| wallet | deposited SOL | fees won | P&L kept | IL cost | return/cycle |
|---|---|---|---|---|---|
| `CMFkL6Pv…` | 59,251 | 1,910 | **+1,156** | -754 | **1.95%** |
| `ReNT8Cke…` | 44,441 | 1,286 | **+890** | -396 | **2.00%** |
| `C7RcE7SW…` | 50,543 | 2,083 | **+442** | -1,641 | **0.88%** |

**All three earn more in fees than they keep.** Impermanent loss takes **31%, 31% and
79%** of gross fees respectively. That is the short-gamma model confirmed on real money
at scale.

**The real return is 0.88%–2.00% per deployed cycle.** Not the 10–50%/day that
`tokleo`'s Fee/TVL implies — that metric is gross fees over liquidity with IL ignored
entirely, and it was never a return.

## 4. The bankroll problem, stated plainly

Operator bankroll is **$500 = ~5 SOL** (SOL ≈ $100).

| wallet | median position | in USD | × the whole bankroll |
|---|---|---|---|
| `CMFkL6Pv…` | 100.0 SOL | $10,003 | **20.0×** |
| `ReNT8Cke…` | 144.6 SOL | $14,462 | **28.9×** |
| `C7RcE7SW…` | 31.4 SOL | $3,145 | **6.3×** |

A copy ratio scales this down, but the return does not scale up. At 1–2% per cycle on
$500 that is **$5–10 per cycle**. Targets, for honesty:

    1 SOL/week ($14.29/day)  needs ~$1,000 at 1.4%/day
    1 SOL/day  ($100.03/day) needs ~$7,150 at 1.4%/day

**$500 does not produce 1 SOL/day at any measured rate.** Anyone claiming otherwise is
quoting turnover, gross fees, or a survivor.

## 5. Why selection is a real edge and not a rationalisation

Because **every public ranking in this space is broken**, verified across ~20 hosted
products and every GitHub repo found:

- Not one corrects for **survivorship**, **luck-vs-skill**, or **sample size**.
- All are a raw P&L sort over a 1d–90d lookback. No minimum-trade gates, no confidence
  intervals, no published methodology.
- **Nansen's labels are literally `30D / 90D / 180D Smart Trader` = "top performers
  (N-day window)".** Survivorship is the product, not a flaw in it.
- The closest thing to genuine vetting on GitHub has **2 stars**. Searches for
  `onchain trader skill luck` and `memecoin trader analysis survivorship` return
  **zero results**.

The Polymarket project's measurement tooling — clustered CIs, minimum-cluster gates,
payout-ceiling checks, bot/human rhythm discrimination — is ahead of everything public
in this category. That asymmetry is the thesis.

**But hold the other possibility honestly:** nobody having built it may mean it does not
work, not that everyone else missed it. Oracle-3 died of exactly this optimism.

## 6. What has to be true for this to pay

Pre-registered, in order. Each kills the project if it fails.

| # | claim | bar | status |
|---|---|---|---|
| T0 | the universe is reachable | ≥100k distinct LP wallets accumulated | **running** — 84.5k in one snapshot, ~160 new/hour |
| T1 | skill is separable from luck | a vs-HODL number per wallet, computed by us | **not built** |
| T2 | skill persists | wallets ranked in period A stay positive in a disjoint period B, CI clear of zero, ≥40 cycles | **not started** |
| T3 | it survives at our size | copy at $500 with real fills for ≥30 cycles, net positive after gas and slippage | **not started** |
| T4 | it is worth the attention | ≥1 SOL/week sustained on the actual bankroll | **not started** |

**T2 is the one that matters.** A leaderboard that cannot predict the next period is a
history book. Every public product fails this and none of them test it.

## 7. Constraints — operator's calls, not findings

- Bankroll **$500**. Do not design for more.
- Execution is **Valhalla** (NFT already owned). Do not build a DLMM bot.
- **He wants real traders, not bots.** Bot-like wallets are explicitly out even when
  they are the most profitable — see the rhythm filter in CLAUDE.md.
- Do not offer opinions on whether he should stop.

## 8. What is settled — do not re-litigate

- **`tokleo` Fee/TVL is gross of IL.** It is the metric that makes a pool look like it
  is printing while every LP in it loses money.
- **Meteora's API cannot enumerate wallets.** Every endpoint requires `user`.
- **`getProgramAccounts` sees only currently-open positions.** Proven blind: wallet
  `3ZhqYVzg…` has 79 closed positions and +3.16 SOL and was absent from an 84,507-wallet
  snapshot.
- **41% of Meteora's own P&L rows are corrupt** (140 of 338 sampled). Any leaderboard
  built on that API without sanity filters is garbage.
- **68.2% of sanity-checked LPs are profitable and the aggregate is NEGATIVE**
  (-8,665 SOL across 198 wallets). Most make small gains; a few get destroyed and
  outweigh everyone. Copying a profitable wallet is a 68% shot at a small gain with a
  fat left tail.
