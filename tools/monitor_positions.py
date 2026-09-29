"""WATCH YOUR OWN DLMM POSITIONS AND SHOUT WHEN ONE BREAKS ITS FLOOR.

Read-only. Takes a PUBLIC address, holds no key, places no order, closes nothing.
It exists because the single highest-value exit rule is unambiguous and mechanical:

    MEASURED on 111,838 closed positions --
      exited IN range        33,876   median  +2.11%   75% win
      exited ABOVE range     56,755   median  +0.18%   75% win
      exited BELOW range     21,165   median  -6.94%   20% win   <- the whole loss pile

Every loss lives in one bucket. You cannot stop-loss your way out of it: the drawdown
when price merely touches your own floor is x/(2-x), so a -50% range is already -33%
at the floor and a -70% range is -54%. Any percentage stop tight enough to fire before
that fires INSIDE your range, while the position is still converting and still earning.

So the trigger is range state, not price. This watches it for you; you click close.

    python3 tools/monitor_positions.py <YOUR_PUBLIC_ADDRESS> [poll_seconds]

Prints a line per change, rings the terminal bell on a floor break, and appends an
audit trail to data/monitor/<addr>.jsonl so a missed alert is still recoverable.
"""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify import push

API = "https://dlmm.datapi.meteora.ag"


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(4):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.4 * (a + 1))
    return None                      # None means FAILED -- never "no positions"


def book(w):
    """-> {pool: {...}} or None if the poll failed. Never confuse the two."""
    rows, pg = [], 1
    while pg < 8:
        d = get(f"{API}/portfolio/open?user={w}&page={pg}&page_size=100")
        if d is None: return None
        rows += d.get("pools") or []
        if not d.get("hasNext"): break
        pg += 1
    out = {}
    for p in rows:
        a = p.get("poolAddress")
        if not a: continue
        dep = float(p.get("totalDepositSol") or 0)
        if dep <= 0: continue
        # WHICH SIDE matters enormously and the flag alone does not say.
        # Below-floor = holding the token, 20% win. Above-ceiling = converted to SOL,
        # 75% win, benign. Alerting identically for both cried wolf on 2026-09-28 when
        # an unfilled bid went out of range UPWARD and pushed an urgent "20% finish
        # green" warning at a position that had simply not activated.
        tokx = float(((p.get("positionValue") or {}).get("tokenX") or {}).get("amount") or 0)
        side = None
        if p.get("outOfRange"):
            side = "below" if tokx > 0 else "above"
        out[a] = {"dep": dep, "pnl": float(p.get("pnlSol") or 0),
                  "oor": bool(p.get("outOfRange")), "side": side,
                  "pct": 100 * float(p.get("pnlSol") or 0) / dep}
    return out


NAMES = {}
def name(a):
    if a not in NAMES:
        d = get(f"{API}/pools/{a}") or {}
        NAMES[a] = d.get("name") or a[:8]
    return NAMES[a]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[-3].strip())
    w = sys.argv[1]
    every = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    os.makedirs("data/monitor", exist_ok=True)
    log = f"data/monitor/{w[:12]}.jsonl"

    def emit(ev):
        with open(log, "a") as fh: fh.write(json.dumps(ev) + "\n")

    state_p = f"data/monitor/{w[:12]}.state.json"
    print(f"  monitoring {w}  every {every}s   log -> {log}")
    print(f"  READ ONLY. It will never close anything -- that is your click.\n")
    # A RESTART MUST NOT LOSE STATE. On 2026-09-28 the monitor restarted, found the
    # position already out of range, logged it as first-sight "seen" and pushed
    # NOTHING -- the operator had zero coverage while being told he had coverage.
    try:
        prev = json.load(open(state_p))
    except Exception:
        prev = {}
    fails = 0
    emit({"t": int(time.time()), "type": "session_start", "wallet": w, "interval": every})
    while True:
        b = book(w)
        if b is None:
            fails += 1
            print(f"  [{time.strftime('%H:%M:%S')}] poll FAILED ({fails}) -- state untouched")
            time.sleep(every); continue
        now = int(time.time())
        for a, v in b.items():
            was = prev.get(a)
            if was is None:
                print(f"  [{time.strftime('%H:%M:%S')}] seen   {name(a):<18} {v['dep']:.3f} SOL "
                      f"{v['pct']:+.1f}%{'  OUT OF RANGE' if v['oor'] else ''}")
                emit({"t": now, "type": "seen", "pool": a, **v})
                # first sight is not "nothing happened" -- if it is ALREADY below the
                # floor he needs to know now, not at the next transition that may never come
                if v["oor"] and v["side"] == "below":
                    push(f"BELOW FLOOR: {name(a)}",
                         f"{v['dep']:.3f} SOL at {v['pct']:+.1f}% - already out when the "
                         f"monitor started, holding the token.\n"
                         f"Only 20% of positions that end below their floor finish green.",
                         "urgent", "rotating_light")
                elif v["oor"]:
                    push(f"Above range: {name(a)}",
                         f"{v['dep']:.3f} SOL, idle - price is past your ceiling so it is "
                         f"earning nothing. Close and re-range to restart the fees.",
                         "default", "arrow_up")
            elif v["oor"] and not was["oor"]:
                if v["side"] == "below":
                    print(f"\a  [{time.strftime('%H:%M:%S')}] *** BELOW FLOOR *** {name(a)}  "
                          f"{v['dep']:.3f} SOL  {v['pct']:+.1f}%")
                    push(f"BELOW FLOOR: {name(a)}",
                         f"{v['dep']:.3f} SOL at {v['pct']:+.1f}% - you are holding the token.\n"
                         f"Only 20% of positions that end below their floor finish green.\n"
                         f"Decide now, do not wait for the bounce.", "urgent", "rotating_light")
                else:
                    print(f"  [{time.strftime('%H:%M:%S')}] above range  {name(a)}  "
                          f"{v['dep']:.3f} SOL  {v['pct']:+.1f}%  (earning nothing)")
                    push(f"Above range: {name(a)}",
                         f"{v['dep']:.3f} SOL at {v['pct']:+.1f}%. Price rose past your ceiling,\n"
                         f"so the position is idle - no loss, but no fees either.\n"
                         f"Close and re-range at the current price to start earning again.",
                         "default", "arrow_up")
                print(f"      20% of positions that END below their floor finish green. "
                      f"Decide now, do not wait for the bounce.")
                emit({"t": now, "type": "out_of_range", "pool": a, **v})
            elif was["oor"] and not v["oor"]:
                print(f"  [{time.strftime('%H:%M:%S')}] back in range {name(a)}  {v['pct']:+.1f}%")
                emit({"t": now, "type": "back_in_range", "pool": a, **v})
        for a, v in prev.items():
            if a not in b:
                print(f"  [{time.strftime('%H:%M:%S')}] closed {name(a):<18} last {v['pct']:+.1f}%")
                emit({"t": now, "type": "gone", "pool": a, **v})
        prev = b
        try:
            tmp = state_p + ".tmp"
            with open(tmp, "w") as fh: json.dump(b, fh)
            os.replace(tmp, state_p)
        except Exception as e:
            print(f"  [state write failed: {e}]")
        oor = sum(1 for v in b.values() if v["oor"])
        dep = sum(v["dep"] for v in b.values()); pnl = sum(v["pnl"] for v in b.values())
        print(f"  [{time.strftime('%H:%M:%S')}] {len(b)} open, {oor} out of range, "
              f"{dep:.2f} SOL deployed, {pnl:+.3f} SOL ({100*pnl/max(dep,1e-9):+.1f}%)")
        time.sleep(every)


if __name__ == "__main__":
    main()
