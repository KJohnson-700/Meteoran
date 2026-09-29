# HANDOVER — Meteoran, updated 2026-09-13 (forward recorder live)

Fresh-chat entry point. Read `THESIS.md`, then `CLAUDE.md` (rules 1–21), then this.

## One paragraph

Provide liquidity on Meteora DLMM by copying wallets that are measurably good at it.
Execution is `Valhalla` (SOL Decoder), NFT already owned, so execution is not where the
edge is. **The entire project is selection.** As of 2026-09-12: 86k wallets discovered,
2,849 measured on vs-HODL LP skill, **T2 (out-of-sample) PASSED at both levels**, and
**rule 11's level question is RESOLVED** — the high positive rate is not an artifact of
our method. A new gate (rule 16, censoring) then **cut the wallet this project had named
its best pick 24 hours earlier.** No capital deployed, no order-placement code here.

## LIVE SINCE 2026-09-17 — CAPITAL IS DEPLOYED (by the operator, via Valhalla)

The operator funded Valhalla (~5 SOL) and enabled copying on 2026-09-17. This project
still contains no keys and no order code; the deployment is his, in his tool. Roster:
`68zXQchy…` (swapped IN for `Dc386eft…` at his call — Dc carried 25 SOL of open
positions at -78%, drag -0.87pp, legal under the gate but too close to the rule-16
pattern for his risk tolerance), `4Cho1WQi…`, `E67mtq97…`. Config: 1 concurrent
position/wallet, global cap 3, max 1.5 SOL/copy, Any-entry mode (SOL-only slice
measured near-zero edge), -35% SL (measured cost ~0, caps a position near -0.5 SOL),
NO take-profit ever (tail carries 83% of P&L), OOR backstop 1440m (2880 for 4Cho),
above-range close ON, token-age/MC/Jup filters loosened after measuring the defaults
blocked ~57% of Dc's entries. Weekly duty now MANDATORY: `vet.py` all three; a wallet
that fails comes out of Valhalla same day. Watch drag lines and JIT signs.

## THE TWO COMMANDS THAT MATTER

```bash
python3 tools/vet.py <any-wallet-address>   # vet: every validated gate, verdict + why, ~15s
./tools/refresh_shortlist.sh                # find: weekly universe -> shortlist_final.json
```

`vet.py` reproduces ground truth: Dc386eft -> COPY CANDIDATE; 24Ku7Cc9 -> REJECT (open
book, all-in -2.16%); 7VxJLbMq -> REJECT (hold, 1m median). B is printed as a range over
cut dates per rule 20. `build_shortlist.py` re-derives the same 14 finalists from disk.

## RUNNING RIGHT NOW — CHECK THESE FIRST

| what | how | why it matters |
|---|---|---|
| `tools/run_forward_recorder.sh 60` | nohup, polls every 60s | **the only live data in the project.** A missed entry cannot be refetched. |
| `tools/run_dlmm_universe.sh` | nohup, hourly | universe accumulation; pauses cost little |

**The recorder has run continuously since first launch 2026-09-13 02:29 PDT** (the
earlier same-night events were deliberately wiped when the baseline-vs-entry bug was
fixed — that was a reset, not an outage; the machine does not sleep, uptime 21 days).
The wrapper restarts on crash but NOT on reboot — add a LaunchAgent if the Mac ever
restarts. **DETECTION LAG IS MEASURED (2026-09-13, 10.7h, n=26): median 35s, p75 45s, max 63s,
100% under 5 minutes.** Rule 18 assumed 300s; the truth is ~9x better. At the 60s column
of `data/paper_replay.json` the shortlist keeps **93-97% of edge** (vs 82-93% assumed).
Caveat: one Saturday of polling — confirm the distribution holds on weekdays before
re-running `follow_sim.py` with the corrected haircut. First live session also caught
1 exit (+31.1% on 1.79 SOL, 3.07h hold) that on-chain RPC independently confirms closed.
Both entry positions verified on-chain: owner program, dataSize 8120, owner pubkey at
offset 40 all match. Verification re-run 2026-09-13: identity 386/386, cross-endpoint
0.0000 SOL, 4/6 published rows reproduce exactly and the other 2 land inside their
published ranges.

```bash
python3 tools/forward_report.py          # what the recorder has actually seen
tail -3 logs/forward_recorder.log        # is it alive
./tools/run_forward_recorder.sh 60 &     # restart if dead
python3 tools/dlmm_universe.py --stats   # universe size
```

## THE FORWARD RECORDER — what it is for

Everything else in this project reads Meteora's historical API and trusts it. Rule 2
measured **30% of their P&L rows as corrupt**, and the rule-20 consistency checks cannot
close that gap: consistent-and-wrong is possible if their indexer is systematically off.

The recorder polls `/portfolio/open` for the top 8 shortlist wallets and writes an
**append-only** `data/forward/events.jsonl` with its own timestamps, so a later rewrite of
their history cannot silently change what we recorded. It reads only — no keys, no
capital, no order placement.

**The number it exists to produce is DETECTION LAG**: position `createdAt` vs the moment a
poller first sees it. Rule 18 *assumed* 5 minutes and derived 82–93% edge retention from
that assumption. This measures it. When there are dozens of entries, re-run rule 18 with
the real figure and then re-run `follow_sim.py` out of sample.

Two design points that are not optional, both already bitten:
- a failed poll must leave state **untouched** — reading it as "no open positions"
  fabricates a full set of phantom exits
- positions open at startup are `baseline`, never `entry`. The first version logged 106 of
  them as entries, which would have filled the lag distribution with multi-day values.

**Status: started 2026-09-13 09:29 UTC, 106 baseline positions, 0 entries yet.** That is
expected — these wallets open a few positions a day. Hours to days before it says anything.

## HOW DO YOU KNOW ANY OF THIS IS REAL?

The operator asked directly, and it is the right question. Three tools now answer it, and
none of them import the pipeline they are checking.

**The data is real and internally consistent.** On `E67mtq97`:
- `pnlSol == withdrawalSol + feeSol - depositSol` holds on **385/385 rows**, largest
  violation **0.000000 SOL**
- `/portfolio/total` equals the sum of `/portfolio` rows to **−0.0000 SOL**
- per-position sums match their pool row's deposit to **0.0000 SOL**
- raw responses + SHA-256 are saved to `data/verify/`, and Solscan links are printed so
  any claim can be checked outside this repo entirely

**Internal consistency is not verification of a published figure.** The first check
recomputed **+14.2% skill** where the shortlist published **+4.94%** — a different window
at a different aggregation level. A wrong number with a good explanation looks exactly
like a fabricated one. Reproducing the EXACT claim (same period, same aggregation, clean
refetch, independent arithmetic): **4 of 6 rows reproduced.**

**The other two were FALSE PRECISION — and the first explanation was wrong.** "Time drift
in a NOW-relative cut" was tested by shifting the cut a day and got WORSE (3/6). Sweeping
the cut 90d→155d: **median spread 0.46pp, worst 2.30pp**, and 2 of 6 published values sit
just outside their own range.

**So quote ranges.** `E67mtq97` is "+3.5% to +5.8%", never "+4.94%". T2 validated the
RANKING (rho +0.38 out of sample) and the rank order is stable across every cut. The
levels never had two decimals in them.

**What is still NOT verified:** that Meteora's own numbers are correct. Rule 2 measured
30% of their P&L rows as corrupt. Every check above tests self-consistency and our
arithmetic, not their ground truth. The only thing that closes that is forward recording
against on-chain state.

## READ THIS FIRST — two gates were added after the shortlist looked settled

**Rule 16 (censoring).** `24Ku7Cc9…` was the pick on 2026-09-11. It passed T1, T2, the
leak-free split and the concentration gate — **+5.23% out-of-sample over 767 positions at
92% beat-HODL**. It was also carrying **81 open positions, 77 out of range, median age 75
days, each down 90–97%, nothing withdrawn**. Realised P&L only counts positions the LP
CHOSE to close. All-in it is **−2.06%**. Across all 2,840 measured wallets, **193 (6.8%)
read profitable on realised P&L and are negative all-in.**

**Rule 17 (hold time).** The rhythm filter reads `lastClosedAt` — one timestamp per POOL
— so it catches a 24/7 bot and is blind to one that trades in human hours and holds each
position for 90 seconds. Per-position timestamps are not blind to it. **4 of the 18
finalists are JIT**: `7VxJLbMq…` holds a median **81 seconds** with 79% of positions under
5 minutes. Uncopyable through Valhalla at any bankroll.
**Do NOT gate on round position sizes** — that is what any automation tool produces,
including the Valhalla the operator runs himself. Gate on duration.

**All 176 T2 survivors have now had the leak-free per-position treatment** (previously
only the top 15). Attrition: 173 measured → 161 positive in A → 148 in B → **114 after
the concentration gate** → 98 all-in positive → 96 → 18 with real evidence and the right
size → **14 copyable**.

## EXECUTION — measured, and rule 14 finally closed

Everything before today backtested the SELECTION rule. This tests what a copier actually
gets.

**Copy delay costs 12–18%, not 50%.** At a 5-minute delay a follower captures **82–93%**
of the target's fee-earning window (`E67mtq97` 85%, `Dc386eft` 84%, `4Cho1WQi` 88%).
The first version of this said ~50% because it counted "price outside the target's range"
as a copy cost. **At zero delay the same measurement gives 60–76%** — that is 5m candle
resolution plus the fact that one-sided liquidity placed outside the current price is a
normal DLMM strategy. Real drift at 5 minutes: **0 to −2pp**. Always run the control.

**Entry slippage is a non-issue at 5 SOL.** **36–93% of entries are one-sided** — one
token only, no swap, no slippage — and 2 SOL is **0.1–1.6% of current pool TVL** for the
top names. (Measure depth on pools held NOW; historical memecoin pools are drained and
read ~$0 TVL.)

**Rule 14, open since the start, is closed.** At 5 SOL across 3 slots, capital
utilisation is **median 35%**. Simulated follower return over 120 days, with the
selection taken only from data older than the simulated window:

| | |
|---|---|
| median follower return, 120 days | **+18.0%** |
| p25 / p75 | +1.8% / +58.5% |
| capital utilisation | 35% |
| **share of P&L from the 5 best positions** | **83% (median)** |

**The tail is the story.** +18% median on 5 SOL is ~$90 on $500 — real, but 83% of it
comes from five positions. Quote the distribution, never the point estimate.

## THREE ERRORS THE SIMULATOR MADE FIRST — all now guarded in the tool

1. **In-sample.** First run replayed the last 120 days on wallets selected on the last
   120 days: **+60,509% annualised**. Rule 8, one level up. `follow_sim.py` now takes the
   selection list as an argument so it can be built from older data.
2. **Wrong anchor.** The target's own return was P&L / sum-of-deposits — that is capital
   TURNOVER, giving a per-CYCLE rate, compared against the follower's PERIOD return. It
   made the follower look 3× better than the wallet it copies. Period return = P&L /
   average capital deployed.
3. **Banked skill instead of cash.** vs-HODL is LP value minus HODL value; a position can
   be +10% vs-HODL while losing 80% in SOL. That alone overstated the median follower
   **+41.8% vs +18.0%**. **vs-HODL selects the wallet; `pnlSol` is what it pays.**

## T2 — THE GATE, PASSED

**Level 1: does vs-HODL skill persist out of sample?** Rank on period A, score on a
disjoint period B.

| test | result |
|---|---|
| Spearman(A skill → B skill), 120d cut, n=705 | **+0.3822** |
| across cuts 60/90/120/150/180/240d | +0.36, +0.38, +0.38, +0.32, +0.35, +0.27 |
| bootstrap 95% CI (resampling wallets) | **[+0.315, +0.447]** |
| permutation p-value | **0.001** |
| **raw P&L → B skill (rule-9 control)** | **+0.006** (±0.05 at every cut) |
| covered rows only (is the bound faking it?) | **+0.489** — higher, so the bound *dilutes* |
| inside the 0.5–10 SOL band (his size) | **+0.356**, n=359 |

**Level 2: does the SELECTION RULE generalise?** Level 1 still permits picking wallets
using B and then quoting B — rule 8 one level up. So three periods: run the whole live
rule on A+B only, score on untouched C.

| group | n | C pooled | C median |
|---|---|---|---|
| **selected by the rule (A+B only)** | 58 | **+2.142%** | **+2.28%** |
| everyone else | 254 | +0.216% | +1.09% |
| whole field | 312 | +0.226% | +1.23% |

**+1.05pp median uplift, p = 0.0008** vs a random-same-n null. Holds across five splits
(uplift +0.40 to +1.41pp, p 0.0004–0.029).

**What T2 did NOT establish — do not overstate this.**
- **The LEVEL is unproven.** 88% of wallets are positive in C; beat rates are 76–84% in
  every quintile including the worst. Rule 11's bias is still open. **Rank with these
  numbers; do not size an allocation against them.**
- **The pooled-capital quintile spread failed its own control.** Q5−Q1 was +1.68% but
  random ranking reached +1.73% at the same n. Whale-dominated, noisy. Quote Spearman.
- **Level 1 is a floor.** `/portfolio` rows are lifetime-per-pool, so a pool worked on
  both sides of a cut blurs the periods. `tools/t2_exact.py` removes that per-position
  and **flipped the sign on 4 of 17 finalists** — always run it before trusting a wallet.

## THE SHORTLIST — every gate

| wallet | A | B | ex-top3 | A n | B n | beat | med SOL | hold | all-in | type |
|---|---|---|---|---|---|---|---|---|---|---|
| `E67mtq97uUqRjYif9dRqnFhzMQbin8nmcBjAkVm3z4vp` | +8.10% | +4.94% | **+4.08%** | 139 | 230 | 87% | 1.97 | 3.0h | +4.25% | discretionary |
| `Dc386eft7NJiYvvx8HBRbnya9BTnoKbnJnbvPK8xXHcr` | +4.56% | +4.12% | **+3.10%** | 143 | **697** | 82% | 2.00 | 2.7h | +2.60% | discretionary |
| `4Cho1WQiU82dEcaFSkKJGaC1h37pGKXF5rj4BHjFMSLv` | +1.40% | +2.94% | +2.04% | 267 | **697** | 80% | 0.55 | **13.3h** | +9.22% | discretionary |
| `3dVGbM26uqx625Ec7rNbDCNfzmT2TPsxvKvW3Gxk3Eqz` | +4.26% | +2.69% | +1.77% | **497** | 180 | 79% | 2.66 | 12.6h | +1.28% | discretionary |
| `68zXQchynHGwx8HrYd2FCaqSFBizUYWhvRydKeTLChDv` | +1.82% | +1.93% | +1.66% | **650** | 462 | 81% | 1.10 | 6.7h | +1.40% | discretionary |
| `CE8q8PXB6wHPWRdUKH8RgPVQJaP3F41zXk5jKSu1EiFB` | +4.19% | +1.61% | +1.14% | **623** | **522** | 79% | 4.00 | 7.5h | +2.29% | tool-assisted |

**`E67mtq97`** — highest ex-top-3 edge of anything copyable, top-3 pools only 19% of its
skill, open book 0.2% of capital and in profit, 55% distinct sizes. MARIO64, HeeHaw,
Pistacio; SOL-quoted; +54.1 SOL lifetime.

**`Dc386eft`** — the better-evidenced twin: nearly the same edge over **697**
out-of-sample positions instead of 230, 1,083 lifetime, +77.7 SOL.

**`4Cho1WQi`** — best strategy fit: **13.3h median hold**, the operator's own described
rhythm, 0.55 SOL per position, all-in **+9.22%**, +196.0 SOL lifetime, last seen 2h ago.

**Cut:** `24Ku7Cc9` and `A4Dh2ELw` (censoring); `7VxJLbMq`, `ACrHckkz`, `1ApGvE2V`,
`4T8x9dxD` (JIT); `BZrG6oXx` (+3.85% A → **−1.58% B** on the exact split); `9GPeph7p`
(**−0.97%** ex-top-3); `2Kmm` (312h holds, park-and-wait); `ReNT8Cke` (101 SOL/position).
**`AEspQJjH` is demoted, not cut** — 84% round sizes, 14% distinct: a tool, not a trader.

## UNIVERSE — the 100k bar is the wrong target

Discovery decays: **112/hr at hour 6 → 27.6/hr by hour 48**. The docs said 66/hr and
projected ~97k in a week; the real answer is 100k is **20 days** out and a saturating fit
never reaches it.

**But keep it running.** Of the **849 truly unscreened** wallets found since the seed
(63% of "new" were already screened — check this before quoting a yield), **47.5% are
candidates** against a **13.46% seed baseline**. 3.5x enriched, exactly as rule 1
predicted: the point-in-time scan over-samples continuous holders. **Track candidates,
not universe size.**

## RULE 11 — RESOLVED

84.6% positive vs-HODL looked like a bias in our own method. Four mechanisms tested;
together they move the level by **~0.16pp**, nowhere near enough to explain it away.

| mechanism | effect |
|---|---|
| wallet survivorship (do quitters differ?) | **nil** — quitters' median A-skill +0.66% vs survivors' +0.64% |
| truncated left tail (uncovered rows) | **0.029pp** — they really are disasters (median −15.98%) but 0.3% of capital |
| position censoring (open book) | **0.11pp** population-wide — see rule 16, it is a per-wallet tell |
| the exit-price estimator itself | **no detectable bias** — exact vs multi-event positions differ −0.43pp, p=0.154 |

What remains is the real shape of a short-hold high-fee LP payoff: pool-level **74.7%
positive, mean win +3.57%, mean loss −3.63%** — frequent modest wins against losses a
DLMM range CAPS once price exits, while fees keep accruing.

**Quote the capital-weighted +0.21%.** Not the +1.78% unweighted mean, not the +0.46%
median. The level is real, small, and rule 3 explains the gap.

## OTHER CORRECTIONS WORTH KNOWING

1. **Rule 10 was partly WRONG and retired a good wallet.** "SOL per position" everywhere
   upstream was really **SOL per pool** — a wallet opens many positions per pool, so it
   overstates by 4–15x. `C7RcE7SW` reads 70.5 SOL/pool but **4.51 SOL/position**. It was
   always copyable, and it passed T2 over 4,016 + 1,955 positions at 23% top-3.
   `measure_wallets.py` still mislabels that column.
2. **`days_back` is capped at 365** — 366+ is an HTTP 400 on every call, silently eaten
   by retry loops. Cost one wasted fetch run that wrote an empty cache.
3. **`/portfolio/open` beats a position cache for the open book.** A cache built from
   `/portfolio` cannot see open positions in pools whose last close predates the 365d
   window: `A4Dh2ELw` showed 9 open positions that way and has **35**.
4. **Two tooling traps, both fixed, both cost a rebuild.** `tools/t2_exact.py` had no
   `__main__` guard, so importing `flat()` from it silently launched a 176-wallet scan;
   and its cache write was a plain `json.dump`, so killing that run left an 83MB
   truncated file nothing could parse. It now writes via temp-file + rename.

## NEXT, in order

1. **Let the recorder run; check `forward_report.py` daily.** Do not quote detection lag
   until there are dozens of entries. Restart it if it dies.
2. **When lag is measured, re-run rule 18 with the real number**, then re-run
   `follow_sim.py` out of sample with the corrected haircut.
3. **Quote the shortlist as RANGES** (rule 20). Prefer `Dc386eft` (0.44pp spread over 697
   positions) over `E67mtq97` (2.30pp over 230) when the difference is inside both.
4. **Keep accumulating, track CANDIDATES not universe size** (rule 1).
5. **Move rules 16 and 17 upstream into `skill_leaderboard.py`.**
6. **The tail is the real risk.** 83% of follower P&L comes from 5 positions. Decide what
   20 losing cycles does to $500 before any capital moves.

## WHAT NOT TO DO

- **Do not build a DLMM bot.** Weeks to reach parity with Valhalla, which he owns.
- **Do not ask for or handle his private key.** Ever.
- **Do not quote vs-HODL as an expected return.** T2 validated the RANKING, not the level.
- **Do not rank on raw P&L.** +0.006 against out-of-sample skill. This is the whole point.
- **Do not trust a coarse `/portfolio` split** for an individual wallet — run `t2_exact`.
- **Do not read "avgPos" in `measure_wallets.py` as position size.** It is per pool.
- **Do not use `dlmm-api.meteora.ag`**, and do not send `days_back` over 365.
- **Do not trust a realised-P&L number without checking the open book.** Rule 16 cut the
  best wallet on the board, and its realised record was excellent right up to that point.
- **Do not judge bot-vs-human from pool-level timestamps alone.** Rule 17: hold time is
  only visible per position, and it cut 4 more finalists.
- **Do not gate on round position sizes.** That is what a tool user looks like, and the
  operator is about to become one.
- **Do not sum vs-HODL as if it were a return.** It is a skill metric. `pnlSol` is cash.
- **Do not run `follow_sim.py` on a selection built from the window it simulates.**
- **Do not quote a copy haircut without the zero-delay control.**
- **Do not quote a B-skill to two decimals.** The cut date alone moves it 0.5-2.3pp.
- **Do not accept "internally consistent" as verification of a published number.**
  Reproduce the exact claim, same window, same aggregation, from a clean refetch.

## Money, unchanged

```
  SOL ~ $100      bankroll $500 = ~5 SOL
  E67mtq97 runs 1.97 SOL per position, ~3h holds -- followable at this size
  4Cho1WQi runs 0.55 SOL at 13.3h holds -- the closest match to his own described rhythm
  the population level is +0.21% capital-weighted per cycle, not the +2% a finalist shows
  measured follow sim: median +18% over 120 days at 5 SOL = ~$90 on $500
  ... of which a median 83% comes from FIVE positions. It is a tail, not an income.
```
**$500 does not produce 1 SOL/day at any measured rate.** Anyone claiming otherwise is
quoting turnover, gross fees, or a survivor.

## Predecessor

`~/Documents/Oracle-3` — Polymarket, six months, **zero strategies cleared their own
bar**. The difference here is that the bar was set first and has now been cleared, on a
period the selection never saw. That is one gate, not a guarantee: the level is still
unproven and nothing has been tested against live execution.
