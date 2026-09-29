"""THE leaderboard: rank 8,263 filtered wallets on vs-HODL LP SKILL, not raw P&L.

We measured (rule 9) that raw pnl_sol rank has Spearman -0.231 against LP skill -- it
carries no positive information. So this does the expensive thing at scale: pull every
wallet's per-pool history, run T1 (vs_hodl) on it, and run the rule-5 rhythm filter in
the SAME pass since the same pool rows carry lastClosedAt.

Stores only the per-wallet summary. Raw pool rows for 8k wallets would be ~400MB and we
only need them again for the final shortlist.

Resumable: re-run to continue. Checkpoints every 250 wallets.
"""
import json, os, sys, time, collections, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "tools")
from vs_hodl import f, vs_hodl

OUT, WORKERS = "data/skill_leaderboard.json", int(sys.argv[1]) if len(sys.argv) > 1 else 16
API = "https://dlmm.datapi.meteora.ag"

def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                             "Accept": "application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(r, timeout=25) as x: return json.loads(x.read())
        except Exception: time.sleep(0.3 * (a + 1))
    return {}

def one(rec):
    w, out = rec["w"], []
    for pg in range(1, 11):
        d = get(f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100")
        out += d.get("pools") or []
        if not d.get("hasNext"): break
    if not out: return None

    dep = sk = beta = fees = 0.0
    used = 0; beat = 0; und = udep = upnl = 0.0; un = 0
    for p in out:
        d0 = f(p, "totalDepositSol")
        if d0 <= 0: continue
        r = vs_hodl(p)
        if r is None:
            un += 1; udep += d0; upnl += f(p, "pnlSol"); continue
        v, h, _ = r
        dep += d0; sk += v; beta += h; fees += f(p, "totalFeeSol")
        used += 1; beat += v > 0
    if used < 10 or dep <= 0: return None

    ts = [int(p["lastClosedAt"]) for p in out if p.get("lastClosedAt")]
    rhythm = {}
    if len(ts) >= 25:
        hrs = collections.Counter(time.gmtime(t).tm_hour for t in ts)
        best = min(sum(hrs[(h + i) % 24] for i in range(6)) for h in range(24))
        days = collections.Counter(time.strftime("%Y-%m-%d", time.gmtime(t)) for t in ts)
        span = (max(ts) - min(ts)) / 86400.0
        rhythm = {"sleep": best / len(ts), "per_day": len(ts) / max(1, len(days)),
                  "off": 1 - len(days) / max(1, span), "span": span}
    return {"w": w, "closed": rec["closed"], "raw_pnl": rec["pnl_sol"],
            "pools": used, "uncovered": un, "dep": dep, "skill": sk, "beta": beta,
            "fees": fees, "beat_rate": beat / used,
            "skill_pct": sk / dep, "skill_pct_bounded": (sk + upnl) / (dep + udep),
            **rhythm}

def ok(r):
    return (abs(r["pnl_sol"]) < 50_000 and abs(r["pnl_usd"]) < 5_000_000
            and r["pct_sol"] > -1.0 and abs(r["pct_sol"]) < 10
            and r["pnl_sol"] * r["pnl_usd"] >= 0)

todo = [r for r in json.load(open("data/dlmm_pnl.json"))
        if ok(r) and 20 <= r["closed"] <= 2000]
res = json.load(open(OUT)) if os.path.exists(OUT) else []
done = {r["w"] for r in res}
todo = [r for r in todo if r["w"] not in done]
print(f"  todo {len(todo):,}  already done {len(done):,}", flush=True)

t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(one, todo), 1):
        if r: res.append(r)
        if i % 250 == 0:
            json.dump(res, open(OUT, "w"))
            el = time.time() - t0
            print(f"  {i:,}/{len(todo):,}  {i/el:.1f} wal/s  kept {len(res):,}  "
                  f"eta {(len(todo)-i)/max(i/el,1e-9)/60:.0f} min", flush=True)
json.dump(res, open(OUT, "w"))
print(f"  DONE {len(res):,} wallets with T1, {time.time()-t0:.0f}s -> {OUT}")
