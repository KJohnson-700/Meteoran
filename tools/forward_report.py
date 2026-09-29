"""Read the forward recorder's append-only log and report what was OBSERVED.

The number this exists to produce is DETECTION LAG: how long after a target opens a
position does a poller actually see it. Rule 18 assumed 5 minutes and derived an 82-93%
edge-retention from that assumption. This replaces the assumption with a measurement.

Nothing here is derived from Meteora's history -- only from what the recorder saw, with
its own clock. That is the point: rule 2 measured 30% of their P&L rows as corrupt, so a
record that depends on their history being right cannot check their history.

Usage: python3 tools/forward_report.py
"""
import json, os, sys, time, statistics as st

EV = "data/forward/events.jsonl"
if not os.path.exists(EV):
    print("  no events yet -- start tools/run_forward_recorder.sh"); sys.exit()

evs = [json.loads(l) for l in open(EV) if l.strip()]
by = lambda t: [e for e in evs if e["type"] == t]
ticks, ents, exits = by("tick"), by("entry"), by("exit")
base, fails = by("baseline"), by("poll_failed")
if not ticks:
    print("  recorder has not completed a tick yet"); sys.exit()

t0, t1 = min(e["t"] for e in evs), max(e["t"] for e in evs)
hrs = (t1 - t0) / 3600
print(f"\n  FORWARD RECORD  {time.strftime('%Y-%m-%d %H:%M', time.gmtime(t0))} -> "
      f"{time.strftime('%H:%M', time.gmtime(t1))} UTC   {hrs:.2f}h   {len(ticks)} ticks")
print(f"  baseline positions {len(base)}   entries {len(ents)}   exits {len(exits)}"
      f"   failed polls {len(fails)}")
if hrs < 0.5:
    print(f"\n  TOO EARLY. Detection lag needs entries, and these wallets open a few")
    print(f"  positions a day. Give it hours, not minutes.")

lags = sorted(e["lag_s"] for e in ents if e.get("lag_s") is not None and e["lag_s"] >= 0)
print(f"\n  DETECTION LAG -- createdAt to first observation")
if len(lags) < 3:
    print(f"    {len(lags)} observed so far; need more before quoting a distribution.")
else:
    n = len(lags)
    print(f"    n {n}   min {lags[0]}s   p25 {lags[n//4]}s   median {lags[n//2]}s"
          f"   p75 {lags[3*n//4]}s   max {lags[-1]}s")
    print(f"    under 60s {100*sum(1 for x in lags if x<60)/n:.0f}%"
          f"   under 300s {100*sum(1 for x in lags if x<300)/n:.0f}%")
    print(f"    -> rule 18 assumed a 5-minute delay; observed median is "
          f"{lags[n//2]}s ({lags[n//2]/60:.1f} min)")

if exits:
    holds = sorted((e["closed"] - e["created"]) / 3600 for e in exits
                   if e.get("closed") and e.get("created"))
    pnls = [(e.get("pnl_sol") or 0) / e["dep"] for e in exits if e.get("dep")]
    print(f"\n  EXITS OBSERVED  {len(exits)}")
    if holds:
        print(f"    hold time  median {holds[len(holds)//2]:.1f}h   "
              f"min {holds[0]:.2f}h   max {holds[-1]:.1f}h")
    if pnls:
        w = sum(1 for x in pnls if x > 0)
        print(f"    realised   median {100*st.median(pnls):+.2f}%   "
              f"win rate {100*w/len(pnls):.0f}% of {len(pnls)}")

if ents:
    per = {}
    for e in ents: per[e["w"]] = per.get(e["w"], 0) + 1
    print(f"\n  ENTRIES BY WALLET (per hour)")
    for w, c in sorted(per.items(), key=lambda kv: -kv[1]):
        print(f"    {w:<46}{c:>4}   {c/max(hrs,1e-9):>5.2f}/h")

if fails:
    print(f"\n  {len(fails)} failed polls -- state was left untouched on each, so no")
    print(f"  phantom exits were recorded. Check the API if this grows.")
