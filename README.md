# Meteoran

Measurement tooling for **Meteora DLMM** liquidity provision on Solana.

**Read-only by design.** No private keys, no order placement, nothing here can open or
close a position. It finds pools, measures them, and watches positions you opened
yourself. Every recommendation ends at a number you type into Meteora.

## What it measured

All of it from Meteora's public API, reproducible from the endpoints named in each tool.

| finding | numbers | sample |
|---|---|---|
| **Fee capture determines outcome, monotonically** | <0.5% fee yield → +0.0% median / 52% win · >25% → **+29.4% / 83% win** | 111,838 closed positions |
| **Impermanent loss is not the enemy** | fees **+5.99%** vs IL **−1.60%** — fees cover IL **3.74x**. Token beta is what kills positions. | 2,811 positions |
| **Every loss lives in one bucket** | exit in range +2.11% / 75% win · above range +0.18% / 75% · **below floor −6.94% / 20% win** | 111,838 |
| **Entry timing**, pre-entry price reconstructed from candles | falling −30..−10% → −3.4% mean / 44% win · pumped +50..+150% → **+2.7% / 72%** · vertical >+150% → −0.9% despite 75% win | 913 |
| **Range headroom above entry** | none → 0.09% fee yield · **25–60% above → 3.60% yield, +3.94% mean** | 1,062 |
| **Raw P&L says nothing about LP skill** | Spearman **−0.231** | 85,976 screened |
| **Small accounts are not disadvantaged** | <50 SOL deployed → **+0.75% median skill**, higher than >5,000 SOL at +0.55% | 2,154 wallets |
| **A stop loss is not a cap** | a 35% stop executed at **55.06%**; 20% executed at 26.6% | live fills |
| Drawdown when price merely touches your own floor | `x / (2 − x)` — a −50% range is already **−33%** at the floor | arithmetic |

`GET /pools` enumerates all ~132,000 pools with no wallet and sorts server-side
(`fee_tvl_ratio_1h:desc`; windows 30m/1h/2h/4h/12h/24h). `fee_tvl_ratio` **is already a
percent** — do not scale it.

## Tools

```
tools/pick_pool.py          rank live pools by fee/TVL
tools/pool_alert.py         continuous scan + push; gates are measured, not guessed
tools/monitor_positions.py  watch your own positions, alert on a floor break
tools/dashboard.py          local live board at http://localhost:8787
tools/heartbeat.py          hourly markdown brief
tools/vet.py                twelve-gate wallet vetting
tools/watch.py              sweep a roster's full open book
tools/vs_hodl.py            split P&L into token beta vs real LP skill
```

`CLAUDE.md` carries rules 1–27 — each one cost something to learn, and several record a
wrong answer that was shipped before it was caught.

## Setup

```bash
cp tools/notify.example.py tools/notify.py   # set TOPIC to something unguessable
echo "<your public wallet>" > data/operator_wallet.txt
python3 tools/pick_pool.py 12h 20 --min-tvl 50000
```

Python 3.9+, standard library only.

## Not included

The operator's wallet address, alert topic, rendered dashboards, and ~320 MB of API
caches are gitignored. The caches rebuild from the API; the rest is personal.

## Caveats worth reading before trusting a number

- Ranking on a **backward-looking window is the main failure mode**. A pool showing
  39.7%/day on 24h earned $384 in its last hour and was already dead. Always read the
  30m/1h/4h/12h/24h ladder as **incremental slices**, not cumulative totals.
- Levels are quoted as **ranges**, never decimals — sweeping the measurement cut moves
  them by up to 2.3pp.
- Simulation can refute, never confirm. Backtested numbers here are upper bounds: no
  slippage, no missed fills.
