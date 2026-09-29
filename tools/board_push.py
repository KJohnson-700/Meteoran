"""Build the snapshot the browser board reads. Read-only.

Writes data/board_state.json. Something with the Artifact tool then pushes it:

    Artifact action=write_db url=<board url> db_op=set
            collection=state doc_id=current file_path=data/board_state.json

The board live-updates the instant that lands. It CANNOT poll on its own -- a published
artifact is behind a strict CSP and can reach neither the Meteora API nor localhost --
so when nobody pushes, the board shows how stale it is and the phone alerts take over.
"""
import json, os, sys, time, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The board URL is private to the operator -- kept out of the repo.
# Put it in data/board_url.txt (gitignored) if you use board_push.
_bu = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "board_url.txt")
BOARD_URL = open(_bu).read().strip() if os.path.exists(_bu) else "<set data/board_url.txt>"

sys.argv = [sys.argv[0]]
_s = importlib.util.spec_from_file_location("mp", os.path.join(ROOT, "tools", "monitor_positions.py"))
mp = importlib.util.module_from_spec(_s); _s.loader.exec_module(mp)


def snapshot(w):
    b = mp.book(w)
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "positions": [], "dep": 0.0, "pnl_pct": 0.0}
    if b is None:
        out["error"] = "poll failed"          # never silently render as "no positions"
        return out
    for a, v in sorted(b.items(), key=lambda kv: kv[1]["pnl"]):
        out["positions"].append({"pool": mp.name(a), "dep": v["dep"], "pct": v["pct"],
                                 "oor": v["oor"], "side": v.get("side")})
    out["dep"] = sum(p["dep"] for p in out["positions"])
    if out["dep"] > 0:
        out["pnl_pct"] = 100 * sum(b[a]["pnl"] for a in b) / out["dep"]
    return out


if __name__ == "__main__":
    wf = os.path.join(ROOT, "data", "operator_wallet.txt")
    w = open(wf).read().strip() if os.path.exists(wf) else None
    if not w: sys.exit("no wallet in data/operator_wallet.txt")
    out = snapshot(w)
    p = os.path.join(ROOT, "data", "board_state.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as fh: json.dump(out, fh, indent=1)
    os.replace(tmp, p)
    print(json.dumps(out))
    print(f"\n  -> {p}\n  push with: Artifact write_db url={BOARD_URL} "
          f"db_op=set collection=state doc_id=current file_path=data/board_state.json")
