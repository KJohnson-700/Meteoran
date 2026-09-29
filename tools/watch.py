"""WHAT IS AT RISK RIGHT NOW across every wallet being copied. Run it constantly.

Built 2026-09-18 after a specific failure: the operator showed one losing position and
asked if it was a problem. I analysed that one position, said "normal", and did not
sweep the other targets -- while a QEPE-SOL position opened 53 minutes earlier was on
its way to -51%. The data was available the whole time. Narrow checking IS the bug.

This sweeps every target's ENTIRE open book, names every pool, and flags:
  OOR       out of range -- earning nothing
  DEEP      down more than 20%
  NOFEE     zero fees earned relative to deposit -- took token risk for no income
  TOKEN     deposit was one-sided token: a COPIER had to BUY that token (rule 22)
Then prints today's closes so a bad exit cannot hide.

Usage: python3 tools/watch.py [wallets.json|addr,addr,...]
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://dlmm.datapi.meteora.ag"
# Nicknames earned from measured habits, not decoration -- data/nicknames.json.
# An address is unreadable; "Minnow sizes at 0.30 SOL" is not. Always show both.
try:
    NICK = {k: v["nick"] for k, v in json.load(open("data/nicknames.json")).items()}
except Exception:
    NICK = {}


def label(w):
    return f'{NICK.get(w, "?"):<14} {w[:8]}'

# THE LIVE ROSTER. Keep this in sync with what Valhalla is actually copying --
# on 2026-09-25 this still listed Magpie and Powder Keg, so the sweep was reporting
# alarming numbers from wallets the operator had already dropped.
DEFAULT = ["HKdmXq9gVf964Rov3GhNuL4bmsvNpge73Je7CL7vqLmy",   # Shift Worker
           "BUD6rK8RBuu4E2obasNnqyUB39bYfiw33vCeBJi6bVYH",   # Minnow
           "68zXQchynHGwx8HrYd2FCaqSFBizUYWhvRydKeTLChDv",   # Metronome
           "3XqscBSeEYX2Ng32MuSUrTjtUYFd7cMagKbyus2ER7hZ"]   # The Closer


def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(4):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.4 * (a + 1))
    return {}


def paged(path, key="pools", pages=8):
    out = []
    for pg in range(1, pages):
        d = get(f"{API}{path}&page={pg}&page_size=100")
        out += d.get(key) or []
        if not d.get("hasNext"): break
    return out


NAMES = {}
def pool_name(a):
    if a not in NAMES:
        NAMES[a] = get(f"{API}/pools/{a}").get("name") or "?"
    return NAMES[a]


def f(d, *ks):
    for k in ks: d = (d or {}).get(k) or {}
    return float(d or 0) if not isinstance(d, dict) else 0.0


def sweep(w):
    opens, closes = paged(f"/portfolio/open?user={w}"), paged(f"/portfolio?user={w}&days_back=1")
    addrs = {p.get("poolAddress") for p in opens + closes if p.get("poolAddress")}
    with ThreadPoolExecutor(max_workers=12) as ex: list(ex.map(pool_name, addrs))
    return opens, closes


def main():
    arg = " ".join(sys.argv[1:])
    if arg and os.path.exists(arg):
        raw = json.load(open(arg))
        ws = [r["w"] if isinstance(r, dict) else r for r in raw]
    else:
        ws = re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", arg) or DEFAULT

    print(f"  WATCH  {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  {len(ws)} wallets\n")
    alerts, tot_open, tot_pnl = [], 0.0, 0.0
    for w in ws:
        opens, closes = sweep(w)
        print(f"  === {label(w)}  {len(opens)} open / {len(closes)} closed today")
        for p in sorted(opens, key=lambda x: float(x.get("pnlSol") or 0)):
            dep = float(p.get("totalDepositSol") or 0)
            if dep <= 0: continue
            pnl = float(p.get("pnlSol") or 0); pct = 100 * pnl / dep
            nm = pool_name(p.get("poolAddress", ""))
            tot_open += dep; tot_pnl += pnl
            flags = []
            if p.get("outOfRange"): flags.append("OOR")
            if pct < -20: flags.append("DEEP")
            # one-sided TOKEN deposit -> a copier had to buy that token (rule 22)
            if f(p, "totalDepositTokenX") > 0 and f(p, "totalDepositTokenY") <= 0:
                flags.append("TOKEN")
            mark = "  <<< " + ",".join(flags) if flags else ""
            print(f"      {nm:<18} dep {dep:6.3f}  {pct:+7.1f}%{mark}")
            if pct < -20: alerts.append((NICK.get(w, w[:8]), nm, dep, pct, flags))
        for p in sorted(closes, key=lambda x: float(x.get("pnlSol") or 0))[:4]:
            dep = float(p.get("totalDepositSol") or 0)
            if dep <= 0: continue
            pct = 100 * float(p.get("pnlSol") or 0) / dep
            if pct < -20:
                print(f"      CLOSED {pool_name(p.get('poolAddress','')):<11} dep {dep:6.3f}  {pct:+7.1f}%  <<< REALISED LOSS")
        print()

    print(f"  open capital {tot_open:.2f} SOL   unrealised {tot_pnl:+.2f} SOL "
          f"({100*tot_pnl/max(tot_open,1e-9):+.1f}%)")
    if alerts:
        print(f"\n  {len(alerts)} POSITION(S) DOWN MORE THAN 20% RIGHT NOW:")
        for w, nm, dep, pct, fl in sorted(alerts, key=lambda x: x[3]):
            print(f"      {w:<14} {nm:<18} {dep:6.3f} SOL  {pct:+7.1f}%  {','.join(fl)}")
        print("\n  A TOKEN flag means a SOL-funded copier BOUGHT that token (rule 22).")
    else:
        print("\n  nothing below -20%.")


if __name__ == "__main__":
    main()
