"""Screen every accumulated wallet through /portfolio/total.

Measured throughput against the free API: 73-361 wallets/sec with no errors, so the
whole universe screens in well under an hour. This is why no paid CSV/batch scanner is
worth anything to us -- the Pro tiers cap at ~2,000 wallet scans PER DAY.

Stores RAW rows. The rule-2 corruption filters (41% of Meteora's P&L rows are junk) are
applied at report time in rank_universe, never at write time -- we keep the junk so the
junk rate stays measurable.

Resumes: already-screened wallets are skipped. Checkpoints every 2,000.
"""
import json, os, sys, time, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

OUT = "data/dlmm_pnl.json"
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 32
API = "https://dlmm.datapi.meteora.ag/portfolio/total?user="

universe = json.load(open("data/dlmm_universe.json"))["wallets"]
rows = json.load(open(OUT)) if os.path.exists(OUT) else []
done = {r["w"] for r in rows}
todo = [w for w in universe if w not in done]
print(f"  universe {len(universe):,}  already screened {len(done):,}  todo {len(todo):,}")

lock, t0 = threading.Lock(), time.time()
fail = [0]

def one(w):
    req = urllib.request.Request(API + w, headers={
        "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
            return {"w": w, "open": universe[w].get("max_open", 0),
                    "pnl_usd": float(d.get("totalPnlUsd") or 0),
                    "pnl_sol": float(d.get("totalPnlSol") or 0),
                    "pct_usd": float(d.get("totalPnlPctChange") or 0),
                    "pct_sol": float(d.get("totalPnlSolPctChange") or 0),
                    "closed": int(d.get("totalClosedPositions") or 0)}
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    with lock: fail[0] += 1
    return None

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(one, todo), 1):
        if r: rows.append(r)
        if i % 2000 == 0:
            json.dump(rows, open(OUT, "w"))
            el = time.time() - t0
            print(f"  {i:,}/{len(todo):,}  {i/el:.0f}/s  failed {fail[0]}  "
                  f"eta {(len(todo)-i)/max(i/el,1e-9)/60:.1f} min", flush=True)

json.dump(rows, open(OUT, "w"))
print(f"  DONE  {len(rows):,} screened total, {fail[0]} unrecoverable, "
      f"{time.time()-t0:.0f}s  -> {OUT}")
