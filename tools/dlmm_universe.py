"""Accumulate the HISTORICAL universe of Meteora DLMM liquidity providers.

`getProgramAccounts` on the DLMM program returns only positions open at the instant
you ask. That is a point-in-time snapshot, and it is biased in exactly the wrong
direction: it over-samples wallets that hold continuously (bots) and under-samples the
profile worth copying -- someone who opens ~15 positions, closes them all inside a day,
and waits. Proof it misses people: 3ZhqYVzg3RsoPhyRWTtGxB6F9LWyRBrpbVQ8bkaAkC1x has 79
closed positions and +3.16 SOL, and was absent from an 84,507-wallet snapshot.

Transaction scanning would fix it but the program does ~200 tx/s, and Meteora's own API
requires `user` on every endpoint so it cannot enumerate.

The cheap fix is to snapshot REPEATEDLY and union. Measured turnover between two
snapshots 41 minutes apart: 109 owners appeared, 86 disappeared -- about 160 new
wallets an hour. Hourly snapshots reach ~111k wallets in a week against 84.5k from one
call, and every wallet that holds a position at ANY point in the window is captured.

    python3 tools/dlmm_universe.py            # one snapshot, union into the store
    python3 tools/dlmm_universe.py --stats    # what we have so far
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time

PROGRAM = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
POSITION_V2_SIZE = 8120          # PositionV2; owner pubkey sits at offset 40
OWNER_OFFSET = 40
RPC = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
STORE = "data/dlmm_universe.json"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + s


def snapshot():
    """Owner -> open position count, right now. One RPC call, ~46MB."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getProgramAccounts",
                       "params": [PROGRAM, {
                           "encoding": "base64",
                           "dataSlice": {"offset": OWNER_OFFSET, "length": 32},
                           "filters": [{"dataSize": POSITION_V2_SIZE}]}]})
    p = subprocess.run(["curl", "-s", "-m", "240", "-X", "POST", RPC,
                        "-H", "Content-Type: application/json", "-d", body],
                       capture_output=True, text=True)
    try:
        rows = json.loads(p.stdout).get("result") or []
    except ValueError:
        return {}
    out = {}
    for r in rows:
        try:
            w = b58(base64.b64decode(r["account"]["data"][0]))
        except Exception:
            continue
        out[w] = out.get(w, 0) + 1
    return out


def load():
    if not os.path.exists(STORE):
        return {"wallets": {}, "snapshots": 0, "first_ts": None, "last_ts": None}
    with open(STORE, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    st = load()
    if a.stats:
        w = st["wallets"]
        if not w:
            print("  store is empty -- run without --stats first")
            return 1
        span = ((st["last_ts"] - st["first_ts"]) / 3600.0) if st["first_ts"] else 0.0
        print(f"  {len(w):,} distinct LP wallets across {st['snapshots']} snapshots "
              f"spanning {span:.1f}h")
        # Guard every derived figure. Two snapshots minutes apart divided by a ~0 span
        # printed "20,286,960 wallets/hour", and called 84,527 of 84,529 wallets
        # bot-like because they appeared in both. Both are artifacts of the window, not
        # findings. A metric that needs a window must refuse to print without one.
        MIN_SNAPSHOTS, MIN_SPAN_H = 6, 4.0
        if st["snapshots"] < MIN_SNAPSHOTS or span < MIN_SPAN_H:
            need_s = max(0, MIN_SNAPSHOTS - st["snapshots"])
            need_h = max(0.0, MIN_SPAN_H - span)
            print(f"  -- no rhythm stats yet: need >={MIN_SNAPSHOTS} snapshots over "
                  f">={MIN_SPAN_H:.0f}h (short by {need_s} snapshots / {need_h:.1f}h).")
            print("     'seen in every snapshot' only means 'holds continuously' once "
                  "the window is")
            print("     long enough for a position to plausibly close inside it.")
            return 0
        always = sum(1 for v in w.values() if v["seen"] == st["snapshots"])
        once = sum(1 for v in w.values() if v["seen"] == 1)
        print(f"  seen in every snapshot (holds continuously, bot-like): {always:,}")
        print(f"  seen exactly once (cycles in and out, human-like):     {once:,}")
        # new-wallet rate, not total/span -- the first snapshot is not "discovery"
        first = st.get("first_snapshot_size") or 0
        if first and span > 0:
            print(f"  new-wallet discovery rate: "
                  f"{(len(w)-first)/span:,.0f}/hour")
        return 0

    snap = snapshot()
    if not snap:
        print("  snapshot failed (RPC refused or truncated); nothing written")
        return 1
    now = int(time.time())
    w = st["wallets"]
    new = 0
    for addr, cnt in snap.items():
        rec = w.get(addr)
        if rec is None:
            w[addr] = {"first": now, "last": now, "seen": 1, "max_open": cnt}
            new += 1
        else:
            rec["last"] = now
            rec["seen"] += 1
            rec["max_open"] = max(rec["max_open"], cnt)
    st["snapshots"] += 1
    if st["snapshots"] == 1:
        st["first_snapshot_size"] = len(snap)
    st["first_ts"] = st["first_ts"] or now
    st["last_ts"] = now
    os.makedirs("data", exist_ok=True)
    with open(STORE, "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    print(f"  snapshot {st['snapshots']}: {len(snap):,} holding now, "
          f"+{new:,} never seen before, universe {len(w):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
