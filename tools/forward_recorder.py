"""FORWARD RECORDER — the only thing in this project that is not a replay of history.

Everything else reads Meteora's historical API and trusts it. Rule 2 measured 30% of
their P&L rows as corrupt, so self-consistency checks (rule 20) cannot close that gap.
This one watches positions appear and resolve in real time and records what it SAW, with
its own timestamps, so the record does not depend on their history being right.

What it captures that history cannot:
  detection lag   position createdAt vs the moment WE first observed it. This is the
                  real copy delay -- rule 18 assumed 5 minutes; this measures it.
                  Positions already open at startup are logged as `baseline`, never as
                  `entry`, or the lag distribution fills with multi-day values.
  entries/exits   append-only event log, so a later rewrite of their history cannot
                  silently change what we recorded.
  live outcome    on exit, the realised pnl and the hold time as observed.

Design notes, all learned the hard way here:
  - atomic writes only (a kill mid-dump once left an 83MB unparseable cache)
  - append-only JSONL for events; the state file is a resume point, not the record
  - resumable: restart picks up from state.json without losing or duplicating events
  - NO capital, NO keys, NO order placement. It only reads.

Usage: python3 tools/forward_recorder.py [INTERVAL_SEC=60] [targets.json]
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 60
SRC = sys.argv[2] if len(sys.argv) > 2 else "data/shortlist_copyable.json"
DIR = "data/forward"
STATE = f"{DIR}/state.json"
EVENTS = f"{DIR}/events.jsonl"
os.makedirs(DIR, exist_ok=True)


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh: json.dump(obj, fh)
    os.replace(tmp, path)


def emit(ev):
    """Append-only. Never rewritten, so the record cannot be silently revised."""
    with open(EVENTS, "a") as fh:
        fh.write(json.dumps(ev, separators=(",", ":")) + "\n")


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.5 * (a + 1))
    return None


def num(v):
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0


def open_book(w):
    """-> {position_address: {pool, dep, pnl, oor}} or None if the API failed."""
    rows, pg = [], 1
    while pg <= 6:
        d = get(f"{API}/portfolio/open?user={w}&page={pg}&page_size=100")
        if d is None: return None                 # never treat a failed poll as "no positions"
        rows += d.get("pools") or []
        if not d.get("hasNext"): break
        pg += 1
    out = {}
    for p in rows:
        lst = p.get("listPositions") or []
        n = max(len(lst), 1)
        for a in lst:
            out[a] = {"pool": p.get("poolAddress"),
                      "dep": num(p.get("totalDepositSol")) / n,
                      "pnl": num(p.get("pnlSol")) / n,
                      "oor": a in (p.get("positionsOutOfRange") or []),
                      "tx": p.get("tokenX"), "ty": p.get("tokenY")}
    return out


def detail(w, pool, addr):
    """One call, only when a position is first seen, to recover its true createdAt."""
    d = get(f"{API}/positions/{pool}/pnl?user={w}&page=1&page_size=100")
    for x in (d or {}).get("positions") or []:
        if x.get("positionAddress") == addr:
            return x
    return None


targets = json.load(open(SRC))
WS = [x["w"] if isinstance(x, dict) else x for x in targets][:8]
state = json.load(open(STATE)) if os.path.exists(STATE) else {}
print(f"  FORWARD RECORDER  {len(WS)} wallets, every {INTERVAL}s", flush=True)
print(f"  events -> {EVENTS}   state -> {STATE}", flush=True)
for w in WS: print(f"    {w}", flush=True)
emit({"t": int(time.time()), "type": "session_start", "wallets": WS, "interval": INTERVAL})

tick = 0
while True:
    tick += 1
    now = int(time.time())
    with ThreadPoolExecutor(max_workers=8) as ex:
        books = dict(zip(WS, ex.map(open_book, WS)))
    ents = exits = 0
    for w, book in books.items():
        if book is None:
            emit({"t": now, "type": "poll_failed", "w": w})
            continue                              # leave state untouched on a failed poll
        first_sight = w not in state
        prev = state.get(w, {})
        for a, v in book.items():
            if a in prev: continue
            if first_sight:
                # Positions already open when the recorder starts are NOT entries. Logging
                # them as such would poison the detection-lag measurement with lags of
                # days, which is the one number this tool exists to produce.
                emit({"t": now, "type": "baseline", "w": w, "pos": a,
                      "pool": v["pool"], "dep": v["dep"]})
                continue
            d = detail(w, v["pool"], a)
            created = int(d.get("createdAt") or 0) if d else 0
            emit({"t": now, "type": "entry", "w": w, "pos": a, "pool": v["pool"],
                  "created": created, "lag_s": (now - created) if created else None,
                  "dep": num(d["allTimeDeposits"]["total"]["sol"]) if d else v["dep"],
                  "pair": f"{v.get('tx')}-{v.get('ty')}", "first_seen": now})
            ents += 1
        for a, v in prev.items():
            if a in book: continue
            d = detail(w, v["pool"], a)
            emit({"t": now, "type": "exit", "w": w, "pos": a, "pool": v["pool"],
                  "created": int(d.get("createdAt") or 0) if d else None,
                  "closed": int(d.get("closedAt") or 0) if d else None,
                  "pnl_sol": num(d.get("pnlSol")) if d else v.get("pnl"),
                  "dep": num(d["allTimeDeposits"]["total"]["sol"]) if d else v.get("dep"),
                  "observed_s": now - int(v.get("seen", now))})
            exits += 1
        for a, v in book.items():
            v["seen"] = prev.get(a, {}).get("seen", now)
        state[w] = book
    save(state, STATE)
    live = sum(len(b) for b in state.values())
    emit({"t": now, "type": "tick", "n": tick, "open": live, "entries": ents, "exits": exits})
    print(f"  [{time.strftime('%H:%M:%S', time.gmtime(now))}] tick {tick}  "
          f"open {live}  +{ents} entries  -{exits} exits", flush=True)
    time.sleep(INTERVAL)
