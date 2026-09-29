# CLAUDE.md — Meteoran

Meteora DLMM liquidity provision on Solana, by copying wallets that are measurably good
at it. Read `THESIS.md` first. **This project is separate from `~/Documents/Oracle-3`
(Polymarket) — do not mix their data, their tools, or their conclusions.**

**Status: measurement only.** There is no capital deployed and no order-placement code
here. Execution is `Valhalla` (SOL Decoder), which the operator runs himself.

## Operator constraints — his calls, not findings

- **Bankroll $500 (~5 SOL).** Every recommendation must work at that size or say
  explicitly that it does not.
- **He wants REAL TRADERS, not bots.** A bot-like wallet is out even when it tops the
  P&L table. Use the rhythm filter below.
- **Execution is Valhalla, NFT already owned.** Marginal cost of using it is zero. Do
  NOT propose building a DLMM bot — bin math, Jito bundles and rebalancing are weeks of
  work to reach parity with a tool he already has.
- **Never ask for or handle his private key.** Valhalla, tracklp and any LP tool are his
  to configure.
- Do not offer opinions about whether he should stop.

## Venue facts — verified against the live API, do not re-derive

**Base URL is `https://dlmm.datapi.meteora.ag`.** NOT `dlmm-api.meteora.ag` — that host
resolves and 404s on every path including root, which cost an hour and a wrong "the API
does not exist" conclusion. Found by pulling the JS bundle from `app.meteora.ag`.

```
GET /api-docs/openapi.json                     113,657 bytes, the real spec
GET /portfolio?user=&days_back=&page=&page_size=    per-pool deposit/fee/withdrawal/pnl
GET /portfolio/total?user=                     totalPnlUsd, totalPnlSol, totalClosedPositions
GET /portfolio/open?user=
GET /positions/{address}/historical            per-event add/remove/claim, USD at block time
GET /positions/{pool_address}/pnl?user=        NOTE: still needs `user`
```

- **`days_back` is HARD-CAPPED AT 365.** 366+ returns HTTP 400 on every call, silently,
  so a retry loop just eats it and returns nothing. Every T1/T2 number in this project is
  therefore a trailing-year measurement.
- **`/portfolio` rows are LIFETIME per pool, stamped with `lastClosedAt`.** `days_back`
  filters WHICH rows come back, it does NOT re-aggregate them to the window — verified by
  pulling the same wallet at 365d and 30d and diffing 116 common pools, all identical.
  So you cannot time-slice a wallet with `/portfolio` alone.
- **`/positions/{pool}/pnl?user=` is the clean time substrate**, and it was missed for
  weeks. It returns one row PER POSITION with `createdAt`, `closedAt`, `isClosed`, and
  the same per-token deposit/withdrawal/fee split in native units and SOL. That makes an
  exact, leak-free period split possible, and `vs_hodl()` reads it unchanged after
  `t2_exact.flat()`. Costs one call per (wallet, pool), so it is for finalists.
- **EVERY endpoint requires `user`. The API cannot enumerate.** It is a lookup, never a
  listing. This is the whole reason the universe has to be built separately.
- The P&L identity holds exactly: `pnlUsd = totalWithdrawal + totalFee - totalDeposit`.
- **Rank on `pnlSol`, never `pnlUsd`** — pnlSol is computed at historical per-event SOL
  price, so it strips the price-of-SOL move. A USD ranking surfaces people who farmed
  during a SOL rally.
- `lastClosedAt` on each pool record is the timestamp that makes bot/human separation
  possible.

**On-chain:**
```
program       LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo
PositionV2    dataSize 8120, owner pubkey at offset 40
scan          getProgramAccounts + dataSlice(40,32) + filter dataSize
              -> ~175,554 positions / ~84,507 owners, ~46MB, ONE free call
```
**Discovery decays AND the 100k bar is the wrong target. MEASURED over 48h / 50
snapshots, `tools/discovery_yield.py`.** New wallets per hour by 6h bucket: **112.7,
53.3, 32.2, 24.0, 31.7, 33.3, 20.3** — settling near **27.6/hour**, not the 66/hour
estimated from the first hours. The seed was 84,529 and 48h added only **2,296**. At that
rate 100k is **20 days** out and a saturating fit never reaches it.

**But counting wallets was always the wrong metric, and the yield proves rule 1 was
right.** Screen the wallets found since the seed: of the **849 truly unscreened** ones
(63% of "new" were already in `dlmm_pnl.json`, which ran 24h into accumulation — check
this before quoting a yield), **47.5% are candidates** (clean, 20-2000 closes) against a
**13.46% seed baseline**, and 62% of them are profitable. A marginal accumulated wallet
is **3.5x more likely to be worth measuring** than a seed wallet, exactly because the
point-in-time scan over-samples continuous holders. 20 more days adds ~4,000 candidates
to the 11,575 the seed produced. **Track candidates, not universe size.**

Public RPC (`api.mainnet-beta.solana.com`) serves this but **intermittently 503s** —
retry, it works. `publicnode` returns 410, `drpc`/`ankr` are gated.

## Measurement rules — every one of these cost something

1. **`getProgramAccounts` sees only CURRENTLY OPEN positions.** It is a point-in-time
   snapshot and it is biased in exactly the wrong direction: it over-samples wallets
   that hold continuously (bots) and under-samples the profile worth copying — someone
   who opens ~15 positions, closes them inside a day, and waits. **Proof:**
   `3ZhqYVzg3RsoPhyRWTtGxB6F9LWyRBrpbVQ8bkaAkC1x` has 79 closed positions and +3.16 SOL
   and did not appear in an 84,507-wallet snapshot. Fix: `tools/dlmm_universe.py` unions
   repeated snapshots. **Measured discovery is ~65-82 new wallets/hour**, not the 160/hour
   first estimated from a single 41-min pair (109 new / 86 gone) - that pair was
   two snapshots and overstated it ~2x. At the observed rate a week reaches **~96k,
   under the 100k T0 bar**. Caveat before acting on that: the three measured hours
   were 03:45-05:45 UTC, the quietest part of the day. Need a full 24h before
   projecting.

2. **30.0% of Meteora's own P&L rows are corrupt** (measured on all 85,976; the
   earlier 41% came from 338 sampled rows). 140 of those 338 failed sanity
   checks — one wallet reports **+1,484,126,984 SOL / +$15.7bn**, another -9.8M SOL
   alongside a POSITIVE $277m. Mandatory filters before any ranking:
   `|pnl_sol| < 50_000` · `|pnl_usd| < 5_000_000` · `pct_sol > -1.0` (worse than -100%
   is impossible) · `|pct_sol| < 10` · `pnl_sol * pnl_usd >= 0` (opposite signs means
   one is broken). Without these the aggregate reads **+1.47 BILLION SOL**.

3. **Never rank on unweighted per-market ROI.** A $1 win at 0.01 prints +9,900%. A naive
   scan reported a **27,082% mean against an 8.5% dollar-weighted return** on the same
   wallet. Weight by cost, or aggregate per window and then cluster.

4. **Fees earned is not P&L kept.** IL took 31%, 31% and 79% of gross fees from the
   three best human LPs. Always report `fees`, `pnl` and `fees - pnl` together. A
   fee-yield number alone (`tokleo`, most dashboards) is gross and misleading.

5. **Bot vs human is measurable from `lastClosedAt`.** Three signals:
   - `sleep6h` — the quietest 6 consecutive UTC hours as a share of all closes. A 24/7
     bot sits near **25%** (6 of 24). The humans measured **0–4%**.
   - `per_day` — closes per ACTIVE day. Humans 2–5. Bots 20+.
   - `off_days` — share of days in span with no activity. Humans 25–84%. Bots ~0%.
   Current filter: `sleep6h < 12%` AND `per_day < 40`. It cut 20 of 53 as bot-like.
   **Position count alone is also a tell**: 22,888 closed positions is a machine.

6. **Sampling caps distort the rhythm metrics.** The profiler reads the most recent N
   pools per wallet. For high-volume wallets that compresses the span and produces
   artifacts (negative off-days). Low-volume wallets — the ones we want — are unaffected.
   State the cap whenever quoting per-day figures.

7. **Realised P&L is not vs-HODL. NOW MEASURED - see `tools/vs_hodl.py`.** Meteora's
   numbers are net of divergence loss but contain **no IL decomposition and no HODL
   benchmark**, so they conflate LP skill with directional token beta. Same trap as the
   HyphyLiquid asset sweep, where the random-entry control revealed ETH was the edge
   rather than the strategy. **It does NOT need `/positions/{addr}/historical`** - the
   `/portfolio` rows already carry `totalDeposit/Withdrawal/Fee` split per token in
   native units AND in SOL, so the exit price of each token is `withdrawalTokenTSol /
   withdrawalTokenT` and the HODL counterfactual is `depositedT * exitPriceT`. Zero extra
   API calls. Identity: `pnlSol = hodl_pnl_sol + vs_hodl_sol`, holds exactly.
   **Coverage is 92-96%.** A row is uncovered when a deposited token was fully converted
   away (withdrawal amount 0), so no exit price exists - and those are **exactly the
   worst-IL cases**, price ran clean through the range. They are 0.6-0.7% of capital, and
   the tool reports a bounded number that charges every one of them its full realised
   loss. Never quote the unbounded figure alone.

8. **A leaderboard that cannot predict the next period is a history book.** Ranking on a
   window and reporting that window's returns is circular. Rank on period A, score on a
   disjoint period B. This is T2 in `THESIS.md` and no public product does it.

9. **Raw P&L rank carries no positive information about LP skill. MEASURED.** T1 run on
   the top 25 wallets by `pnl_sol` out of the 85,976-wallet screen:
   **Spearman rank correlation between raw pnl_sol and bounded vs-HODL skill = -0.231**
   (n=22, noisy, but the sign is not positive). **6 of 25 have zero or negative LP
   skill.** The #1 wallet by raw P&L, `5uvdZTVB…` at **+37,756 SOL, is 100% token beta
   and +0.00% LP skill** — a whale who parked capital and rode the token. `AuDS1jWv…`
   at +14,173 SOL has **-2.24%**: it lost to simply holding. Meanwhile `EpTEt8zm…`
   ranks 11th on raw P&L and carries **+13.49% bounded LP skill across 260 pools at an
   85.8% beat-HODL rate**. This is the single strongest evidence for the thesis, and it
   is why every product that sorts on PnL and win rate — Valyze, GMGN, Nansen — is
   selling a ranking that is uncorrelated with the thing you want to copy.

10. **Size gates must be measured PER POSITION, not per pool. The first version of
    this rule was wrong and retired a good wallet.** `/portfolio` aggregates a pool, and
    a wallet opens many positions in the same pool, so `deposit / pools` overstates true
    position size by 4-15x. Measured per position via `/positions/{pool}/pnl`:
    `CMFkL6Pv` 326 SOL/pool but **median 50 SOL/position**; `ReNT8Cke` 681 -> **143**;
    `C7RcE7SW` 70.5 -> **4.51**. The first two are still far too big and stay retired.
    **`C7RcE7SW` was retired on a metric error — its median position is the bankroll**,
    and it then passed T2 (+1.19% A, +0.83% B over 4,016 and 1,955 positions, top-3 only
    23%). `tools/measure_wallets.py` still labels `dep/pools` as "avgPos"; read it as
    per-POOL. The old shortlist was still selected on P&L, which correlates with size. The T1 leaderboard fixes this: median LP skill
    by capital decile RISES as size falls (+0.46% in the largest decile, +0.94% in the
    smallest), so small LPs are not worse — and `data/size_matched.json` holds **473
    wallets with human rhythm, >=30 pools, positive LP skill and avg position 0.5-10
    SOL**, which is his actual size.

11. **Capital-weighted LP skill across 2,840 measured wallets is +0.208%. The unweighted
    mean is +1.455% — 7x higher.** That gap IS rule 3, quantified on our own data.
    Quote the capital-weighted number. Median per-wallet is +0.69%, so the finalists at
    +2.1-2.3% are above median but not extraordinary.
    **The high positive rate is NOT an artifact of our method — RESOLVED 2026-09-12,
    `tools/bias_level.py`, `tools/bias_estimator.py`, `tools/open_book.py`.** Four
    candidate mechanisms were each measured, and together they move the level by
    ~0.16pp, not by the ~1pp that would be needed to explain it away:
    - **wallet survivorship — NIL.** Wallets that stopped trading before period C had
      median A-skill **+0.66%** against survivors' **+0.64%**. Quitting does not select
      for being bad. Survivor premium **-0.019pp**.
    - **truncated left tail — 0.029pp.** Uncovered rows really are the disasters
      (median **-15.98%** realised, 74% losing) but they are only **0.3% of capital**.
    - **position censoring — ~0.02pp at population scale.** Measured on all 2,840:
      median drag **0.00pp**, p25 -0.06pp. The raw pooled figure reads -4.47% and is
      **three wallets** — `EDZrT3iM…` alone has **10.65 MILLION SOL** parked open.
      Excluding the top 10 by open capital, all-in is +0.172% against realised +0.188%.
      Never quote the unexcluded pooled number. See rule 16: negligible on average,
      lethal for individual wallets.
    - **the exit-price estimator — no detectable bias.** On 400 sampled positions split
      by event history, single-add/single-remove (where the estimator is EXACT) vs
      multi-event differ by **-0.43pp on the median, permutation p = 0.154**.
    What is left is the genuine shape of a short-hold, high-fee LP payoff: at pool level
    **74.7% positive, mean win +3.57%, mean loss -3.63%** — frequent modest wins against
    losses that a DLMM range CAPS once price exits it, while fees keep accruing.
    **So quote the capital-weighted +0.21%.** Not the +1.78% unweighted mean, not the
    +0.46% median. The level is real, small, and rule 3 is why the three differ.

12. **Single-pool performance does not rank wallets. MEASURED against Valyze's own
    output.** Their ANTHROPIC-pool table showed 18 of 30 wallets losing. Resolving 18 of
    them to full addresses and measuring lifetime: `4ZQB…` reads **-0.8 SOL in that pool
    but +32.1 SOL lifetime**; `BDDw…` -0.5 vs **+13.1**; `GzdP…` -0.1 vs **+12.0**;
    `J4tk…` +0.4 vs **+55.7**. One pool is a few percent of a wallet's activity and the
    sign flips constantly. Use pool scans for DISCOVERY ONLY — never read the metrics
    next to the addresses.
    Best find from that one scan: `2Kmm…Rjak`, **+11.26% LP skill over 68 pools at
    6.06 SOL/position**, which their table labelled with a meaningless +4,161.0%. Also
    `8opi…uvEz`, **+5.30% skill while -0.1 SOL lifetime** — it LP'd falling tokens and
    lost less than holding, which raw P&L can never surface.

13. **Concentration gate — added after it nearly cost us. `tools/measure_wallets.py`.**
    `2Kmm…Rjak` measured **+8.40% LP skill over 68 pools at 87% beat rate with textbook
    human rhythm** and was about to be called the best find of the day. Then: **76% of
    all its skill comes from 3 pools, all OPENAI** (41% from one). That is one token and
    one narrative, not a repeatable edge, and it would almost certainly fail T2. Gate is
    `top3 > 65%` -> CONCENTRATED. Note also that 2Kmm holds ~54 days per position over a
    650-day history — a park-and-wait strategy, not the fast-cycle profile Valhalla
    automates.
    The wallet that survives instead is `AEspQJjH…`: only **+0.76% skill**, but over
    **461 pools**, top-3 = 51%, 22% losing pools, sleep6h 0.8%, 43% off-days, **4.24 SOL
    per position**. Lower edge, far more of it real. Prefer sample size over headline.

14. **The "real traders, not bots" constraint costs nothing. MEASURED on 2,049 wallets
    with both T1 and rhythm.** This was worth checking, because a batch of pool-scanned
    wallets showed the best LP skill landing on bot-like rhythms, which would have put
    the operator's constraint in direct conflict with the edge. At scale it does not:
    **human-like median skill +0.74% vs bot-like +0.33%** (capital-weighted +0.321% vs
    +0.206%), and skill falls monotonically with activity rate — **+1.20% per cycle at
    1.0-1.7 closes/day down to +0.46% at 4.3-23.8**. Slow humans earn MORE per deployed
    cycle.
    **Unresolved:** that is per CYCLE, not per year. A wallet doing 12 cycles/day at
    0.46% may out-earn one doing 1.5/day at 1.20% in absolute terms. We have not
    measured capital utilisation, so annualised return is an open question. Do not
    claim humans beat bots outright — claim they beat them per cycle.

15. **T2 PASSED. Measured 2026-09-11, at two levels, and the second one is the one that
    matters.** `tools/t2_oos.py`, `tools/t2_robust.py`, `tools/t2_abc.py`.

    **Level 1 — does vs-HODL skill persist?** Rank on period A, score on disjoint B.
    **Spearman = +0.3822** (n=705, 120d cut), bootstrap 95% CI **[+0.315, +0.447]**,
    permutation p **0.001**. Stable at every cut from 60d to 240d (+0.36, +0.38, +0.38,
    +0.32, +0.35, +0.27). The rule-9 control — **raw P&L -> B skill — is +0.006**, and
    stays inside +/-0.05 at every cut. Restricted to the 0.5-10 SOL band it is **+0.356**
    (n=359). Covered-rows-only is **+0.489**, HIGHER, so the uncovered-row bound dilutes
    the signal rather than creating it.
    **The rank statistic passed; the pooled-capital quintile spread did NOT.** Q5-Q1 was
    +1.68% with CI [+0.37%, +4.22%], but random ranking produced spreads to +1.73% at the
    same n. Pooled capital is whale-dominated. Quote the Spearman, not the spread.

    **Level 2 — does the SELECTION RULE generalise?** Level 1 still lets you pick wallets
    using B and then quote B, which is rule 8 one level up. So: three periods, run the
    whole live rule on A+B only, score on untouched C. Selected wallets earn **+2.14%
    pooled / +2.28% median** in C against a field of **+0.23% / +1.23%** — a **+1.05pp
    median uplift, p = 0.0008** against a random-same-n null. Holds across five splits
    (uplift +0.40 to +1.41pp, p 0.0004-0.029).

    **What this does NOT establish.** The LEVEL is still unproven (rule 11): 88% of
    wallets spanning three periods show positive C, and beat rates sit at 76-84% in
    every quintile including the worst. Use these numbers to RANK. Also, the coarse
    split leaks — a pool worked on both sides of a cut carries its whole lifetime into
    one period — which blurs periods toward the null, so Level 1 is a FLOOR.
    `tools/t2_exact.py` removes it per-position and flipped the sign on 4 of 17
    finalists, so run it before trusting any individual wallet.

16. **THE CENSORING GATE. A wallet that books winners and parks losers reads as skilled
    on every realised metric we have. MEASURED 2026-09-12, `tools/open_book.py`, and it
    killed the wallet this project had just named its best pick.**
    Realised P&L is conditioned on the LP CHOOSING to exit. `24Ku7Cc9…` passed T1, T2,
    the exact per-position split and the concentration gate — +5.23% out-of-sample skill
    over 767 positions at 92% beat-HODL — and was carrying **81 open positions, 77 of
    them out of range, median age 75 days, each down 90-97%, nothing ever withdrawn.**
    All-in it is **-1.51%**, not +5.72%.
    Gate: `all-in = (realised pnl + unrealised pnl) / (closed + open capital)` must be
    positive, and the drag `all-in - realised` must be better than -1pp. Measured on all
    **2,840** wallets: median drag **0.00pp** — this is not a population bias, it is a
    per-wallet tell — but **8.2% carry worse than -1pp, 2.0% worse than -5pp, and 193
    (6.8%) read profitable on realised P&L and are negative all-in.** 3.3% have more
    than a fifth of their capital sitting open.
    **Caveat on what all-in means.** An open position has no exit price, so it cannot be
    decomposed into beta vs skill. All-in P&L is therefore the BOUND (it charges the full
    unrealised loss, some of which is token beta), and realised vs-HODL is the optimistic
    end. Quote both for a wallet you are about to copy. Source is `/portfolio/open`, one call per page, and it is MORE complete
    than a per-position cache built from `/portfolio`, which cannot see open positions
    in pools whose last close predates the 365d window (`A4Dh2ELw…`: 9 open positions
    visible that way, **35** in reality, and -10% not +6%).

16b. **OPEN-POSITION FEES READ AS ZERO. `totalFeeSol` on `/portfolio/open` counts only
    CLAIMED fees, never accrued ones. FOUND 2026-09-18 live, from the operator asking why a
    target showed 0 fees on a position his copy was earning on.** Measured on
    `4Cho1WQi`: **all 53 open pools report `totalFeeSol` exactly 0**, including one at
    **+6.7 SOL on a 4.3 SOL deposit** — impossible for a position up 148%. Closed rows are
    unaffected (the rule-20 identity `pnlSol == withdrawal + fee - deposit` holds 386/386,
    so fees land on close).
    **The accrued fees live in `unrealizedPnl.unclaimedFeeTokenX/Y` on
    `/positions/{pool}/pnl`, and `pnlSol` ALREADY NETS THEM IN.** Verified on the live GP
    position: balances 0.5800 SOL + unclaimed 0.00556 + 0.00664 - deposit 0.6747 =
    **-0.0825, which equals the reported `pnlSol` exactly.** So the first version of this
    rule was WRONG to infer that rule 16 understates open positions — the all-in gate
    reads `pnlSol` and is therefore already fee-inclusive. No gate call changes.
    What IS true: never quote `totalFeeSol` for an open position, and never read its 0 as
    "earned nothing" — this position had earned 0.0122 SOL (+1.8% of deposit) while
    reporting 0.
    A copier's own tool (Valhalla) shows ACCRUED fees, so a copy will look like it is
    out-earning its target when it is not. Compare pnl, not fees, across the two.

17. **HOLD TIME is a bot tell the rhythm filter structurally CANNOT see, and JIT
    strategies are uncopyable at any bankroll. MEASURED 2026-09-12,
    `tools/bot_holdtime.py`.** Rule 5 reads `lastClosedAt` — ONE timestamp per pool — so
    it catches a wallet trading around the clock and is blind to one that trades in human
    hours and holds each position for ninety seconds. Per-POSITION `createdAt`/`closedAt`
    is not blind to it. Of 18 wallets that cleared every other gate, **4 are JIT**:
    `7VxJLbMq…` median hold **81 seconds, 79% of positions under 5 minutes**; `ACrHckkz…`
    4m/58%; `1ApGvE2V…` 7m/44%; `4T8x9dxD…` 7m/42%. Nobody picks a pool, deploys and exits
    inside two minutes a thousand times — that is single-swap liquidity, latency-bound and
    bundle-dependent, and Valhalla cannot reproduce it.
    Gate: **median hold < 10 min, OR >40% of positions under 5 min -> UNCOPYABLE.**
    **Do NOT gate on round position sizes.** It is tempting — `AEspQJjH…` sizes 84% of
    its deposits on round numbers with only 14% distinct values — but that is what ANY
    automation tool produces, including the Valhalla the operator will run himself.
    Rejecting it would reject the exact profile he is trying to become. Report it as
    `tool-assisted` and let him decide; gate on DURATION.

18. **EXECUTION MEASURED — the copy haircut is 12-18%, not 50%. `tools/paper_replay.py`,
    `tools/entry_cost.py`.** A copier learns of a position after it is on chain and enters
    late. Replaying that on history:
    - **catchable x life-left at a 5-minute delay = 82-93%** for the shortlist
      (`E67mtq97` 85%, `Dc386eft` 84%, `4Cho1WQi` 88%, `3dVGbM26` 93%).
    - **ALWAYS RUN THE ZERO-DELAY CONTROL.** The first version measured "is price inside
      the target's range at entry+5m", got 39-81%, and reported a ~50% haircut. At ZERO
      delay the same measurement gives **60-76%** — the shortfall is 5m candle resolution
      plus the fact that **placing one-sided liquidity outside the current price is a
      normal DLMM strategy**, not a failure. Real drift is **0 to -2pp**. Only the delta
      between delayed and zero-delay is a copy cost.
    - **Entry slippage is a non-issue at this bankroll.** **36-93% of entries are
      one-sided** (one token only: no swap, no slippage), and 2 SOL is **0.1-1.6% of
      current pool TVL** for the top names.
    - **Do NOT measure pool depth on historical pools.** A memecoin pool traded six months
      ago is drained today, so current TVL reads ~$0 and position/TVL comes out in the
      millions of percent. Measure depth on the pools the target holds NOW.

19. **RULE 14 CLOSED, and three ways the simulation lied first. `tools/follow_sim.py`.**
    Capital utilisation at 5 SOL with 3 slots: **median 35%**. Simulated follower return
    over 120 days, selection from `data/t2_abc.json` (A+B only, both older than the
    simulated window): **median +18.0%, p25 +1.8%, p75 +58.5%.**
    **It is tail-driven: a median 83% of follower P&L comes from its five best
    positions.** Quote the distribution, never the point estimate.
    Three errors, each of which printed a confident wrong number:
    - **In-sample simulation.** The first run replayed the last 120 days on wallets
      selected on the last 120 days and printed **+60,509% annualised**. Rule 8, one level
      up. Always pass a selection built from data older than the simulated window.
    - **Wrong anchor.** The target's "own return" was P&L / sum-of-deposits. That is
      capital TURNOVER and gives a PER-CYCLE rate, not comparable to the follower's
      PERIOD return; it made the follower look 3x better than the wallet it copies.
      Period return = P&L / average capital deployed = sum(size x duration) / span.
    - **Banking skill instead of cash.** vs-HODL is LP value minus HODL value: a position
      can be +10% vs-HODL while losing 80% in SOL because the token collapsed. Summing
      vs-HODL as a return overstated the median follower at **+41.8% vs +18.0%**.
      **vs-HODL SELECTS the wallet; `pnlSol` is what the wallet PAYS.** For short-hold
      SOL-quoted LPs the two per-cycle rates happen to be close (`Dc386eft` +4.10% cash
      vs +4.12% skill) because token beta averages out — do not assume that holds.

20. **VERIFY THE PUBLISHED NUMBER, NOT AN ADJACENT ONE — and quote ranges.
    `tools/verify_claims.py`, `tools/verify_shortlist.py`, `tools/verify_stability.py`.**
    The operator was right to ask how any of this is checkable. Three findings:
    - **The data is real and internally consistent.** On `E67mtq97`: the identity
      `pnlSol == withdrawalSol + feeSol - depositSol` holds on **385/385 rows, largest
      violation 0.000000 SOL**; `/portfolio/total` equals the sum of `/portfolio` rows to
      **-0.0000 SOL**; per-position sums match their pool row's deposit to **0.0000 SOL**.
      Raw responses and SHA-256s are written to `data/verify/` and Solscan links printed,
      so any claim is checkable outside this toolchain entirely.
    - **Internal consistency is NOT verification of a published figure.** The first
      check recomputed **+14.2% skill** where the shortlist published **+4.94%** — a
      different window at a different aggregation level. A mismatched number with a
      plausible explanation is indistinguishable from a fabricated one. Reproduce the
      EXACT claim: same period, same aggregation, refetched, independent arithmetic.
      Doing that, **4 of 6 published rows reproduced**.
    - **The other two were FALSE PRECISION, not bad data, and the first explanation was
      wrong.** "Time drift in a NOW-relative cut" was tested by moving the cut one day
      and got WORSE (3/6). Sweeping the cut from 90d to 155d: **median spread 0.46pp,
      worst 2.30pp** (`E67mtq97` ranges +3.49% to +5.79%), and **2 of 6 published values
      fall outside their own range** (by 0.04 and 0.14pp).
    **So: quote `E67mtq97` as "+3.5% to +5.8%", never "+4.94%".** The second decimal was
    never real. What T2 validated is the RANKING (rho +0.38 out of sample), and the rank
    order is stable across every cut; the levels are not.

21. **THE FORWARD RECORDER IS RUNNING — the first live data in this project.
    `tools/forward_recorder.py`, `tools/run_forward_recorder.sh`, `tools/forward_report.py`.**
    Every other number here reads Meteora's historical API and trusts it. Rule 2 measured
    **30% of their P&L rows as corrupt**, and rule 20's consistency checks cannot close
    that gap — consistent-and-wrong is possible if their indexer is systematically off.
    This polls `/portfolio/open` for the top 8 shortlist wallets every 60s and writes an
    **append-only** `data/forward/events.jsonl` with its OWN timestamps, so a later
    rewrite of their history cannot silently change what we recorded.
    **The number it exists to produce is DETECTION LAG** — position `createdAt` vs the
    moment a poller first sees it. Rule 18 ASSUMED 5 minutes and derived 82-93% edge
    retention from that assumption; this measures it.
    Design points that are not optional:
    - a failed poll must leave state UNTOUCHED, never be read as "no open positions", or
      it fabricates a full set of phantom exits
    - positions already open at startup are logged `baseline`, NEVER `entry` — the first
      version logged 106 of them as entries, which would have filled the lag distribution
      with multi-day values and made the headline number meaningless
    - atomic writes only; append-only events, `state.json` is a resume point not a record
    - reads only. No keys, no capital, no order placement.
    **It needs hours-to-days before quoting anything.** These wallets open a few positions
    a day; at 0.02h it had 0 entries, which is expected, not a failure.

22. **THE TARGET'S ENTRY IS NOT THE COPIER'S ENTRY, AND THIS COST REAL MONEY
    2026-09-18.** Every edge number in this project measures what the TARGET did. A
    one-sided TOKEN deposit is the target DEPLOYING INVENTORY — often selling it into
    strength. For a SOL-funded copier the identical position is a MARKET BUY of that
    token, taken ~40s later, at whatever price the swap gets. Same shape, opposite trade.
    **Measured share of entries that force a copier to buy the token:** `4Cho1WQi`
    **87%** (63% token-only), `E67mtq97` **70%**, `68zXQchy` **25%**.
    Rule 18 said one-sided entries are "no swap, no slippage" — TRUE FOR THE TARGET,
    FALSE FOR THE COPIER, and it was quoted to the operator as a reason to enable
    swap-entry mode. He then took `E67mtq97`'s QEPE-SOL entry (100% token, 493k QEPE),
    the token halved in 49 minutes, and the copy realised **-51.18%** (-0.346 SOL).
    **SOL-only mode is measured BETTER on two of three:** `E67mtq97` +5.27%/cycle
    SOL-only vs +4.09% all-in; `68zXQchy` +1.73% vs +1.50%; only `4Cho1WQi` loses
    (+1.60% on 142 positions vs +9.08%), and it is the one with 87% swap exposure.
    **Never quote a target-side statistic as a copier-side expectation again.**

23. **A STOP LOSS IS NOT A CAP. MEASURED ON A LIVE FILL.** Valhalla's 35% stop executed
    at **55.06%**. Cause is visible in its own log: it revalues off a MEDIAN of 4 price
    sources, and at exit Jupiter (the executable price) read **$0.00008692** against a
    median of **$0.00010392** — the stop measured 16% above anything tradeable. Add the
    stop-loss timer (which had been raised 2->5 min on my advice, to avoid whipsaws) and
    the fire happens into a hole. Entry-time prices had agreed to 0.00%, so agreement at
    entry says nothing about agreement at exit.
    Set the timer to 1-2 min and the threshold ~15pp tighter than the loss you will
    actually accept. **Never tell the operator a stop "caps" anything.**

24. **A MIN-TVL FILTER IS THE WRONG LEVER — MEASURED, do not re-propose it.** After the
    QEPE loss (pool TVL $162, 24h vol $439, ZERO fees earned) the obvious fix looked like
    a pool-size floor. Measured over 111 positions closed in 7 days: pools under $1k TVL
    returned **+4.2% mean at a 66% win rate**; a $1k floor cuts 34% of trades that were
    net positive. And the worst losers in that bucket were NOT fee-starved — `SI-SOL`
    earned a **20.4% fee yield and lost 59%**, `ZECBALL` **47.6% and lost 11.6%**. The
    mechanism is token collapse, not pool size. Also note current TVL on a pool traded
    days ago is a post-mortem reading (rule 18), so this can only ever be directional.

25. **FEE YIELD IS THE TRADE, AND IT IS MONOTONIC. MEASURED ON 111,838 CLOSED
    POSITIONS ACROSS 179 WALLETS, 2026-09-26 — the strongest single result here.**
    Outcome scales monotonically with how much a position actually earned in fees:

    | fee yield | n | median pnl | win | median hold |
    |---|---|---|---|---|
    | <0.5%  | 45,118 | **+0.0%** | 52% | 0.2h |
    | 0.5-2% | 19,882 | +0.8% | 76% | 1.6h |
    | 2-5%   | 17,438 | +2.3% | 73% | 2.2h |
    | 5-10%  | 12,845 | +4.7% | 69% | 3.4h |
    | 10-25% | 11,533 | +8.9% | 69% | 9.0h |
    | **>25%** | 5,022 | **+29.4%** | **83%** | **23.2h** |

    A position earning nothing is a coin flip that loses on average. Mean turns
    positive only above the 10% band. **This also contradicts the fast-turnover
    advice given to the operator**: fee yield accrues with TIME IN A PRODUCTIVE
    POOL, and the best band sits at 23h, not 12 minutes. The 0.2h band is 40% of
    all positions and the worst one.
    **AND IL IS NOT THE ENEMY.** vs-HODL decomposes exactly as `fees - IL`. On the
    roster's 2,811 SOL-only positions: **fees +5.99%, IL -1.60%, net +4.39% — fees
    cover IL 3.74x.** What kills positions is TOKEN BETA (JACKET -79%, PHAT -68%,
    SCRIBE -61% are dead tokens, not divergence loss). Never let anyone blame IL
    without decomposing it.

26. **THE API CAN ENUMERATE POOLS — the "lookup, never a listing" note was WRONG.
    `GET /pools` needs no `user`, lists all 132,160, and sorts server-side.**
    Fields include `tvl`, `volume`, `fees` and `fee_tvl_ratio` PER TIMEFRAME, plus
    `pool_config` (bin_step, base_fee_pct), `created_at`, `is_blacklisted`.
    - sort syntax is `<field>_<window>:desc`, e.g. `fee_tvl_ratio_1h:desc`. Windows
      **30m/1h/2h/4h/12h/24h sort; 6h and 8h exist in the payload but 400 on sort.**
      A bare field or a `-field` prefix is rejected; direction is mandatory.
    - **`fee_tvl_ratio` IS ALREADY A PERCENT.** Verified against `fees/tvl` on six
      pools, ratio/calc == 1.00 exactly. The first version of `pick_pool.py`
      multiplied by 100 and printed 2051%/hour. Never scale it.
    This makes rule 25 actionable BEFORE entering: `tools/pick_pool.py` ranks live
    pools by the exact quantity that predicts outcome. It still cannot see a rug —
    a high ratio on a tiny young pool is usually one swap, not flow. Prefer
    vol/TVL > 1 and age > 1 day.

27. **DO NOT RE-SURFACE AN OLD CALL AS A NEW FIND, AND DO NOT SELL A NON-EVENT AS A
    SAVE. 2026-09-27, caught by the operator, and it is a TRUST failure not a math one.**
    baton-SOL was pushed to his phone as an urgent entry at 19:59 on 9/26. Eighteen hours
    later, with nothing new qualifying, it was presented again as though the scanner had
    found something. It had not. Re-running a stale recommendation with fresh framing is
    indistinguishable from noise, and it burns the one thing that makes an alert worth
    reading.
    **Same episode, second failure:** at 11:12 on 9/26 baton read 2.0%/day on the 1h and
    the advice was "wait". Price then ran **+72%**, which would have carried a one-sided
    position UP through its range into the "+0.18% median, 75% win" bucket. The wait call
    cost nothing but it SAVED nothing either, and it was described as a save. Never claim
    a counterfactual win without checking what actually happened after.
    **Rules now:**
    - every recommendation carries the timestamp it was FIRST made; if it is a repeat,
      say "this is the same call from <when>, nothing new has qualified"
    - never present the absence of new candidates as a new candidate
    - before crediting a "we avoided that" call, pull the price and check. If the avoided
      thing went up, say so.

## Products surveyed — status and what they cost

| product | cost | what it gives | verdict |
|---|---|---|---|
| **Meteora datapi** | free | per-wallet P&L, positions, events | **the data layer.** Cannot enumerate. |
| **tracklp.com** | free 3 wallets / $29mo Pro | Meteora-LP-specific, finds top LPers BY POOL, bin charts, alerts, one-click copy | **use the free tier.** Ranks on an undisclosed 7-day metric — a window too short to contain a blowup. |
| **lpagent.io** | $10 lifetime (5 RPM) / $20mo (10) / $40mo (20) | historical LP positions, multi-protocol | $10 tier worth it as a **universe-size cross-check only**. Rate limits make bulk screening impossible. |
| **Vybe** | free tier (48h history) / $49mo | trader rankings | **conflicting reports** on whether it has Meteora LP positions. No IL field either way. |
| **Nansen** | paid | "Smart Money" labels | **survivorship by construction** — labels are literally `30D/90D/180D Smart Trader` = "top performers (N-day window)". |
| **Step Finance** | — | was the best Solana LP dashboard | **gone.** `app.step.finance` serves only a staking page now. |
| **GMGN / Birdeye / KolScan** | free/paid | trader boards | raw P&L sorts. GMGN's risk filters screen for bots and scam tokens, not skill. |
| **Valyze** (`app.valyze.org`) | $23/$26/$30 mo | Meteora pool/wallet scanner, 24h board, 0-100 S/A/B/C rating | **enumeration only, and even that is crippled.** TESTED 2026-09-11 on the ANTHROPIC pool: **12 of 30 wallets were NOT in our 85,976-wallet universe** — real rule-1 discovery, the one thing worth having. But it **truncates addresses** (`HcFm...8kJ7`), so results are unusable until matched back by prefix+suffix (`data/valyze_resolved.json` resolved 18/30; the other 12 are lost). Its **% column is mathematically broken** — it prints -3,093.7% and +4,161.0%, impossible for an LP (rule 2: you cannot lose more than you deposit); it divides cumulative P&L by a single position's size. And per-pool P&L is near-useless for ranking: `4ZQB…` reads -0.8 SOL there but is **+32.1 SOL lifetime**. |
| **substreams `meteora-dlmm`** | free to ~7M blocks, then ~$25/TB | per-event add/remove/claim keyed to owner | **the P&L attribution path** if we build vs-HODL. v0.9.0, by 0xMukesh, community not official. |

**No GitHub repo does genuine wallet vetting.** Best prior art is `heil-kaizen/hawkin`
(2★, holder-overlap repeatability). Everything else executes copies, re-serves a hosted
raw-P&L sort, or computes P&L for one wallet you already picked.

## The shortlist — all 176 survivors, every gate, 2026-09-12

Gate attrition after putting **all 176** T2 survivors through the leak-free per-position
split (previously only the top 15 had it):

```
  measured, >=10 positions per period       173
  positive in period A                      161   (-12)
  positive in disjoint period B             148   (-13)
  positive with 3 best B pools removed      114   (-34)   <- rule 13 is the biggest cut
  positive ALL-IN (open book marked)         98   (-16)   <- rule 16
  censoring drag better than -1pp            96    (-2)
  >=100 positions BOTH sides, 0.5-10 SOL,
  ex-top3 >=1%, active in last 14 days       18
  not a JIT strategy                         14   (-4)    <- rule 17
```

**B skill is quoted as a RANGE (rule 20).** Sweeping the cut date 90-155d moves it by a
median 0.46pp and up to 2.30pp, so a two-decimal figure is false precision. The rank
order is stable across every cut; the levels are not.

| wallet | A | B skill (range) | ex-top3 | A n | B n | beat | med SOL | hold | all-in | type |
|---|---|---|---|---|---|---|---|---|---|---|
| `E67mtq97uUqRjYif9dRqnFhzMQbin8nmcBjAkVm3z4vp` | +8.1% | **+3.5% to +5.8%** | +4.1% | 139 | 230 | 87% | 1.97 | 3.0h | +4.3% | discretionary |
| `Dc386eft7NJiYvvx8HBRbnya9BTnoKbnJnbvPK8xXHcr` | +4.6% | **+3.9% to +4.3%** | +3.1% | 143 | **697** | 82% | 2.00 | 2.7h | +2.6% | discretionary |
| `4Cho1WQiU82dEcaFSkKJGaC1h37pGKXF5rj4BHjFMSLv` | +1.4% | +2.9% to +3.7% | +2.0% | 267 | **697** | 80% | 0.55 | **13.3h** | +9.2% | discretionary |
| `3dVGbM26uqx625Ec7rNbDCNfzmT2TPsxvKvW3Gxk3Eqz` | +4.3% | +2.8% to +3.1% | +1.8% | **497** | 180 | 79% | 2.66 | 12.6h | +1.3% | discretionary |
| `68zXQchynHGwx8HrYd2FCaqSFBizUYWhvRydKeTLChDv` | +1.8% | +1.9% | +1.7% | **650** | 462 | 81% | 1.10 | 6.7h | +1.4% | discretionary |
| `CE8q8PXB6wHPWRdUKH8RgPVQJaP3F41zXk5jKSu1EiFB` | +4.2% | +1.6% | +1.1% | **623** | **522** | 79% | 4.00 | 7.5h | +2.3% | tool-assisted |

**`Dc386eft` is the most trustworthy number on the board** — a 0.44pp spread over 697
out-of-sample positions. `E67mtq97` has the higher headline and a **2.30pp** spread over
230; prefer the tighter one when the difference is inside both ranges.

**`E67mtq97` holds the top spot** — highest ex-top-3 edge of anything copyable, 87%
beat-HODL, top-3 pools only 19% of its skill, open book 0.2% of capital and in profit,
3.0h holds, 55% distinct position sizes (genuinely discretionary). Trades MARIO64,
HeeHaw, Pistacio, quoted in SOL. Lifetime +54.1 SOL.

**`Dc386eft` is the better-evidenced twin**: nearly the same edge over **697**
out-of-sample positions instead of 230, 1,083 lifetime, 2.7h holds, +77.7 SOL lifetime.
If you want one name backed by the most data at a real edge, it is this one.

**`4Cho1WQi` is the best strategy fit**: **13.3h median hold** — the operator's own
described rhythm — 697 out-of-sample positions, 0.55 SOL each (followable at any size),
all-in **+9.22%**, +196.0 SOL lifetime, last seen 2 hours ago.

**Excluded by rule 17 (JIT, uncopyable):** `7VxJLbMq…` (81s median hold, 79% under 5min),
`ACrHckkz…`, `1ApGvE2V…`, `4T8x9dxD…`.

**`AEspQJjH` is demoted, not cut.** It clears every statistical gate but sizes **84% of
deposits on round numbers with only 14% distinct values** — a tool with preset sizes, not
a discretionary trader. Still copyable; just know what it is.

**`24Ku7Cc9` remains cut** on rule 16 (81 positions rotting at -88%, all-in -2.06%).

## Hermes vault

`~/Documents/Hermes Second Brain/projects/meteoran/` — INDEX.md carries the measured
findings and the operating rules in condensed form so a fresh session does not re-derive
them or repeat the execution mistakes. `findings/2026-09-27-behavioural-failures.md` is
the list of seven ways this project lost money, none of which were analysis errors.
Keep both in sync when a rule here changes.

## Layout

```
tools/pick_pool.py          RULE 25/26: rank all 132k live pools by expected fee yield
tools/watch.py              sweep every copied wallet's full book, flag anything <-20%
tools/vet.py                THE OPERATOR TOOL: full gate stack on any pasted address,
                            verdict + reasons in ~15s. Use this on every tip/scan find.
tools/refresh_shortlist.sh  THE WEEKLY PIPELINE: universe -> gates -> shortlist_final.json
tools/build_shortlist.py    joins t2_exact + open_book + hold_tells into the final table
tools/dlmm_universe.py      snapshot + union the LP universe (hourly, free)
tools/discovery_yield.py    is more accumulation worth it -- candidates, not wallets
tools/bot_holdtime.py       RULE 17: per-position hold time; JIT vs tool vs discretionary
tools/paper_replay.py       RULE 18: copy-delay haircut, with the zero-delay control
tools/entry_cost.py         one-sided entries + pool depth for a 2 SOL copier
tools/follow_sim.py         RULE 19: bankroll-constrained follow sim. RUN OUT OF SAMPLE.
tools/verify_claims.py      RULE 20: raw capture + identity + cross-endpoint, no imports
tools/verify_shortlist.py   reproduces the EXACT published figures from a clean refetch
tools/verify_stability.py   how far a published number moves when the cut date moves
tools/forward_recorder.py   RULE 21: live polling, append-only event log. READS ONLY.
tools/run_forward_recorder.sh  keep-alive wrapper; restarts on crash
tools/forward_report.py     detection lag / entries / exits from the observed record
tools/run_dlmm_universe.sh  the accumulator loop
tools/fetch_pnl.py          batch /portfolio/total for a wallet list
tools/bot_vs_human.py       rhythm filter: sleep6h, per_day, off_days
tools/profile_wallet.py     full per-wallet breakdown: tokens, sizes, fees, IL
tools/vs_hodl.py            T1: splits pnl into token beta vs real LP skill
tools/pick_pools.py         which pools to feed an external scanner for wallet ENUMERATION
tools/screen_universe.py    /portfolio/total for every accumulated wallet, ~112/s, resumable
tools/rank_universe.py      rule-2 + rule-5 filters, then candidates
tools/profile_candidates.py per-pool pull + T1 on the candidates
tools/skill_leaderboard.py  T1 + rhythm at scale -> data/skill_leaderboard.json
tools/measure_wallets.py    full stack on an ad-hoc address list (paste from a pool scan)
tools/counterfactual.py     clustered CIs (ported from Oracle-3)
tools/t2_fetch.py           caches dated per-pool rows for every measured wallet
tools/t2_oos.py             T2 level 1: rank on A, score on disjoint B
tools/t2_robust.py          attacks that result: cut sweep, permutation, bound, size band
tools/t2_survivors.py       the live selection rule -> data/t2_survivors.json
tools/t2_exact.py           T2 EXACT: per-POSITION split, no leakage, + ex-top3 gate
tools/t2_abc.py             T2 level 2: does the SELECTION RULE generalise to period C
tools/t2_finalists.py       recency, hold time, position size, tokens for the survivors
tools/open_book.py          RULE 16: marks the open book to market -> all-in return
tools/bias_level.py         attacks rule 11: survivorship, truncation, censoring, shape
tools/bias_estimator.py     attacks the vs-HODL exit-price estimator itself
data/meteora_openapi.json   the API spec, cached
data/vs_hodl.json           the T1 output
data/t2_pools.json          144MB, dated pool rows, 2,849 wallets -- re-split for free
data/t2_positions.json      per-position cache for the finalists
data/t2_survivors.json      176 wallets passing the full live rule
data/t2_exact.json          leak-free A/B + concentration for the finalists
data/t2_abc.json            the level-2 result
data/open_book.json         all-in return + censoring drag for the 176 survivors
data/shortlist_final.json   what survives every gate including rule 16
data/shortlist_all.json     all 96 wallets clearing every statistical gate
data/shortlist_copyable.json the 14 that are also copyable through Valhalla
data/open_book_all.json     censoring screen over all 2,840 measured wallets
data/paper_replay.json      edge kept at 1/5/15/30/60-minute copy delays
data/entry_cost.json        one-sided share + current pool depth
data/follow_sim.json        follower P&L, utilisation, tail concentration
data/valyze_scan_list.md    the tiered pool list handed to Valyze 2026-09-11
```

## Commands

```bash
python3 tools/vet.py <address> [...]      # vet ANY wallet, all gates, ~15s each
./tools/refresh_shortlist.sh              # weekly: rebuild the whole shortlist
./tools/refresh_shortlist.sh --fast       # re-gate without re-screening the universe
python3 tools/dlmm_universe.py            # one snapshot into the store
python3 tools/dlmm_universe.py --stats    # universe size, bot/human split
./tools/run_dlmm_universe.sh &            # hourly accumulation
python3 tools/fetch_pnl.py                # P&L for the accumulated wallets
python3 tools/bot_vs_human.py             # filter to human-like
python3 tools/profile_wallet.py           # what the finalists actually trade
python3 tools/t2_fetch.py 20              # cache dated pool rows (resumable, ~2 min)
python3 tools/t2_oos.py 120 8             # T2 level 1
python3 tools/t2_robust.py                # the robustness battery
python3 tools/t2_abc.py 240 120 6         # T2 level 2 -- the real gate
python3 tools/t2_survivors.py 120         # apply the live rule
python3 tools/t2_exact.py 120 data/t2_finalists.json   # leak-free, finalists only
python3 tools/t2_finalists.py             # recency / hold / size / tokens
python3 tools/open_book.py data/t2_survivors.json   # RULE 16, the censoring gate
python3 tools/bias_level.py               # the rule-11 battery
python3 tools/bias_estimator.py 400       # is the estimator itself biased
python3 tools/bot_holdtime.py             # RULE 17: JIT detection from hold time
python3 tools/discovery_yield.py          # is more accumulation still paying
python3 tools/paper_replay.py             # RULE 18: what survives a 5-minute delay
python3 tools/entry_cost.py data/shortlist_copyable.json 2.0 100
python3 tools/follow_sim.py 5 3 120 data/t2_abc.json    # RULE 19 -- note the selection arg
python3 tools/verify_claims.py <wallet>   # RULE 20: is the underlying data consistent
python3 tools/verify_shortlist.py 120     # do the PUBLISHED numbers reproduce
python3 tools/verify_stability.py         # how much false precision is in them
./tools/run_forward_recorder.sh 60 &      # RULE 21: live recorder (keep it alive)
python3 tools/forward_report.py           # what has actually been observed
```

## Next, in order

1. **Let the forward recorder run; check `tools/forward_report.py` daily.** It is the only
   live evidence in the project. Do not quote detection lag until there are dozens of
   entries — hours to days, not minutes. If it dies, restart
   `./tools/run_forward_recorder.sh 60 &`; a missed entry cannot be refetched.
2. **When lag is measured, re-run rule 18 with the real number** instead of the assumed
   5 minutes, then re-run `tools/follow_sim.py` out of sample with the corrected haircut.
3. **Quote the shortlist as RANGES everywhere** (rule 20). Prefer `Dc386eft` (0.44pp
   spread over 697 positions) to `E67mtq97` (2.30pp over 230) when the difference sits
   inside both ranges.
4. **Keep accumulating, track CANDIDATES not universe size** (rule 1) — truly-new wallets
   are 3.5x enriched. Weekly: `screen_universe.py` -> `skill_leaderboard.py` ->
   `t2_fetch.py` -> `open_book.py` -> `bot_holdtime.py`.
5. **Move rules 16 and 17 upstream into `skill_leaderboard.py`** so censoring wallets and
   JIT bots never reach a shortlist.
6. **The tail is the real risk, not the level.** A median 83% of follower P&L comes from
   5 positions. Before any capital, decide what a run of 20 losing cycles does to $500.

See `HANDOVER.md` for the current shortlist and the Valyze verdict.
