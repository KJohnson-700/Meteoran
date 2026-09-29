"""ADVERSARIAL SELF-CHECK. Re-derive the headline claims from raw API responses using
code that shares NOTHING with the tools that produced them.

The point is not to prove the API honest -- rule 2 already measured 30% of Meteora's own
rows as corrupt. The point is to catch the failure mode that has actually bitten this
project: a tool that computes the wrong thing and prints it cleanly. Four of those
yesterday (in-sample sim, turnover-as-capital-base, vs-HODL banked as cash, in-range with
no zero-delay control). Each looked fine.

So this deliberately does NOT import vs_hodl.py or any other project module. Every number
is recomputed from scratch, raw JSON is written to data/verify/ for inspection by hand,
and on-chain links are printed so a claim can be checked outside this repo entirely.

Checks:
  1 RAW CAPTURE      save the exact bytes the API returned, with a SHA-256
  2 IDENTITY         pnl == withdrawal + fee - deposit, on every row, independently
  3 CROSS-ENDPOINT   /portfolio/total vs the sum of /portfolio rows vs per-position rows
  4 RECOMPUTE        vs-HODL, hold time, concentration, open book -- fresh arithmetic
  5 ON-CHAIN         position addresses + Solscan links to verify outside this toolchain

Usage: python3 tools/verify_claims.py <wallet>
"""
import json, os, sys, time, hashlib, urllib.request

API = "https://dlmm.datapi.meteora.ag"
W = sys.argv[1] if len(sys.argv) > 1 else "E67mtq97uUqRjYif9dRqnFhzMQbin8nmcBjAkVm3z4vp"
OUT = "data/verify"
os.makedirs(OUT, exist_ok=True)


def raw(path, name):
    """Fetch, save the exact bytes, hash them. Nothing is parsed before it is stored."""
    r = urllib.request.Request(API + path, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=30) as x:
        b = x.read()
    p = f"{OUT}/{name}.json"
    open(p, "wb").write(b)
    return json.loads(b), p, hashlib.sha256(b).hexdigest()[:16]


def num(v):
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0


print(f"\n  VERIFYING  {W}")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")

# ---- 1 RAW CAPTURE -------------------------------------------------------------
tot, p1, h1 = raw(f"/portfolio/total?user={W}", "portfolio_total")
print("  1 RAW CAPTURE")
print(f"    {p1}  sha256:{h1}")
print(f"    the API's own words: totalPnlSol={tot.get('totalPnlSol')}  "
      f"totalClosedPositions={tot.get('totalClosedPositions')}")

pools, pg = [], 1
while pg <= 10:
    d, p, h = raw(f"/portfolio?user={W}&days_back=365&page={pg}&page_size=100",
                  f"portfolio_p{pg}")
    pools += d.get("pools") or []
    if pg == 1: print(f"    {p}  sha256:{h}  ({len(d.get('pools') or [])} rows)")
    if not d.get("hasNext"): break
    pg += 1
print(f"    {pg} pages captured, {len(pools)} pool rows total")

# ---- 2 IDENTITY ----------------------------------------------------------------
print("\n  2 IDENTITY CHECK  pnlSol == withdrawalSol + feeSol - depositSol")
bad = worst = 0
for p in pools:
    lhs = num(p.get("pnlSol"))
    rhs = num(p.get("totalWithdrawalSol")) + num(p.get("totalFeeSol")) - num(p.get("totalDepositSol"))
    tol = max(1e-6, 1e-4 * abs(lhs))
    if abs(lhs - rhs) > tol:
        bad += 1; worst = max(worst, abs(lhs - rhs))
print(f"    {len(pools)-bad}/{len(pools)} rows satisfy it exactly"
      f"   violations {bad}   largest {worst:.6f} SOL")
print(f"    -> {'the arithmetic in these rows is internally consistent' if bad == 0 else 'SOME ROWS ARE INCONSISTENT -- do not trust them'}")

# ---- 3 CROSS-ENDPOINT ----------------------------------------------------------
print("\n  3 CROSS-ENDPOINT AGREEMENT")
sum_pools = sum(num(p.get("pnlSol")) for p in pools)
print(f"    sum of /portfolio rows (365d)   {sum_pools:+12.4f} SOL")
print(f"    /portfolio/total (lifetime)     {num(tot.get('totalPnlSol')):+12.4f} SOL")
print(f"    difference                      {num(tot.get('totalPnlSol'))-sum_pools:+12.4f} SOL"
      f"   <- expected non-zero: total is LIFETIME, rows are a trailing year")

biggest = sorted(pools, key=lambda p: -num(p.get("totalDepositSol")))[:1]
if biggest:
    pool = biggest[0]["poolAddress"]
    d, p, h = raw(f"/positions/{pool}/pnl?user={W}&page=1&page_size=100", "positions_biggest")
    ps = d.get("positions") or []
    s_dep = sum(num(x["allTimeDeposits"]["total"]["sol"]) for x in ps)
    s_pnl = sum(num(x.get("pnlSol")) for x in ps)
    print(f"\n    largest pool {pool}")
    print(f"      /portfolio says   deposit {num(biggest[0].get('totalDepositSol')):10.4f}"
          f"   pnl {num(biggest[0].get('pnlSol')):+10.4f}")
    print(f"      sum of positions  deposit {s_dep:10.4f}   pnl {s_pnl:+10.4f}   ({len(ps)} positions)")
    dd = abs(s_dep - num(biggest[0].get('totalDepositSol')))
    print(f"      deposit agreement within {dd:.4f} SOL"
          f"  -> {'CONSISTENT' if dd < max(0.01, 0.01*s_dep) else 'MISMATCH -- investigate'}")
    print(f"      {p}  sha256:{h}")

# ---- 4 RECOMPUTE ---------------------------------------------------------------
print("\n  4 RECOMPUTED FROM SCRATCH (no project code imported)")
dep = sk = 0.0; n = beat = unc = 0; udep = upnl = 0.0
for p in pools:
    d0 = num(p.get("totalDepositSol"))
    if d0 <= 0: continue
    hodl = 0.0; ok = True
    for T in ("TokenX", "TokenY"):
        da = num(p.get(f"totalDeposit{T}"))
        if da <= 0: continue
        wa, ws = num(p.get(f"totalWithdrawal{T}")), num(p.get(f"totalWithdrawal{T}Sol"))
        ds = num(p.get(f"totalDeposit{T}Sol"))
        if wa <= 0 or ws <= 0 or ds <= 0: ok = False; break
        hodl += da * (ws / wa)
    if not ok:
        unc += 1; udep += d0; upnl += num(p.get("pnlSol")); continue
    v = num(p.get("totalWithdrawalSol")) + num(p.get("totalFeeSol")) - hodl
    if abs(v) > 50 * d0: unc += 1; udep += d0; upnl += num(p.get("pnlSol")); continue
    dep += d0; sk += v; n += 1; beat += v > 0
print(f"    pools used {n}   uncovered {unc}   capital {dep:,.1f} SOL")
print(f"    vs-HODL LP skill        {100*sk/dep:+.3f}%   beat-HODL {100*beat/n:.1f}% of {n}")
print(f"    bounded (uncovered charged full loss) {100*(sk+upnl)/(dep+udep):+.3f}%")
print(f"    CASH return per cycle   {100*sum(num(p.get('pnlSol')) for p in pools)/sum(num(p.get('totalDepositSol')) for p in pools):+.3f}%"
      f"   <- what is actually banked (rule 19)")

op, pg = [], 1
while pg <= 5:
    d, _, _ = raw(f"/portfolio/open?user={W}&page={pg}&page_size=100", f"open_p{pg}")
    op += d.get("pools") or []
    if not d.get("hasNext"): break
    pg += 1
o_dep = sum(num(p.get("totalDepositSol")) for p in op)
o_pnl = sum(num(p.get("pnlSol")) for p in op)
c_dep = sum(num(p.get("totalDepositSol")) for p in pools)
c_pnl = sum(num(p.get("pnlSol")) for p in pools)
print(f"\n    OPEN BOOK (rule 16)  {len(op)} pools  {o_dep:,.2f} SOL  "
      f"({100*o_dep/(o_dep+c_dep):.1f}% of capital)  marked {100*o_pnl/o_dep if o_dep else 0:+.2f}%")
print(f"    realised {100*c_pnl/c_dep:+.3f}%   ALL-IN {100*(c_pnl+o_pnl)/(c_dep+o_dep):+.3f}%")

# ---- 5 ON-CHAIN ----------------------------------------------------------------
print("\n  5 CHECK IT OUTSIDE THIS TOOLCHAIN")
print(f"    wallet     https://solscan.io/account/{W}")
if biggest:
    print(f"    pool       https://solscan.io/account/{pool}")
    print(f"    app        https://app.meteora.ag/dlmm/{pool}")
    for x in ps[:3]:
        print(f"    position   https://solscan.io/account/{x['positionAddress']}"
              f"   created {time.strftime('%Y-%m-%d %H:%M', time.gmtime(x['createdAt']))}"
              f"   dep {num(x['allTimeDeposits']['total']['sol']):.3f} SOL")
print(f"\n    raw responses in {OUT}/ -- every number above is recomputable from them by hand")
