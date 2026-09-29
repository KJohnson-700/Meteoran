"""T1 -- vs-HODL decomposition.

Meteora's pnlSol is net of divergence loss but has NO HODL benchmark, so it conflates
LP skill with directional token beta. This splits them:

    pnl_sol  =  hodl_pnl_sol  +  vs_hodl_sol
                (token beta)     (what LPing actually added)

Per pool, entirely from /portfolio rows (no extra API calls):
    exit price of token T, in SOL   =  totalWithdrawalTokenTSol / totalWithdrawalTokenT
    HODL value at exit              =  sum over T of  depositedT * exitPriceT
    LP value at exit                =  totalWithdrawalSol + totalFeeSol

CAVEAT, stated wherever this is quoted: a position with several adds/removes at
different times aggregates into one row, so the implied exit price is a value-weighted
average over withdrawal events, not a point price. Exact for single-add/single-remove.
Rows where a deposited token was fully converted away (withdrawal amount 0) have no
derivable exit price and are reported as uncovered, never silently dropped.
"""
import json, sys, statistics as st

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/three_pools.json"

def f(p, k):
    try: return float(p.get(k) or 0)
    except (TypeError, ValueError): return 0.0

def vs_hodl(p):
    """-> (vs_hodl_sol, hodl_pnl_sol, deposit_sol) or None if not derivable."""
    dep = f(p, "totalDepositSol")
    if dep <= 0: return None
    hodl = 0.0
    for T in ("TokenX", "TokenY"):
        d_amt = f(p, f"totalDeposit{T}")
        if d_amt <= 0: continue
        w_amt, w_sol = f(p, f"totalWithdrawal{T}"), f(p, f"totalWithdrawal{T}Sol")
        if w_amt <= 0 or w_sol <= 0: return None          # no exit price derivable
        d_sol = f(p, f"totalDeposit{T}Sol")
        if d_sol <= 0: return None
        px_out, px_in = w_sol / w_amt, d_sol / d_amt
        if not (1e-9 < px_out / px_in < 1e9): return None  # corrupt price row
        hodl += d_amt * px_out
    lp = f(p, "totalWithdrawalSol") + f(p, "totalFeeSol")
    v, h = lp - hodl, hodl - dep
    if abs(v) > 50 * dep or abs(h) > 50 * dep: return None # rule-2 style sanity
    return v, h, dep

def report(name, pools):
    rows, uncovered, dropped_dep = [], 0, 0
    for p in pools:
        if f(p, "totalDepositSol") <= 0: dropped_dep += 1; continue
        r = vs_hodl(p)
        if r is None: uncovered += 1
        else: rows.append((r, p))
    n = len(rows)
    print(f"\n  === {name} ===")
    if not n:
        print("    nothing computable"); return None
    tot_dep = sum(r[2] for r, _ in rows)
    tot_v   = sum(r[0] for r, _ in rows)
    tot_h   = sum(r[1] for r, _ in rows)
    tot_pnl = sum(f(p, "pnlSol") for _, p in rows)
    fees    = sum(f(p, "totalFeeSol") for _, p in rows)
    beat    = sum(1 for r, _ in rows if r[0] > 0)
    per     = sorted(r[0] / r[2] for r, _ in rows)
    print(f"    pools used          {n}   uncovered {uncovered}   zero-deposit {dropped_dep}")
    print(f"    capital deployed    {tot_dep:,.1f} SOL   fees earned {fees:+,.1f} SOL")
    print(f"    realised pnl        {tot_pnl:+,.1f} SOL   ({100*tot_pnl/tot_dep:+.2f}% of deployed)")
    print(f"      = token beta      {tot_h:+,.1f} SOL   ({100*tot_h/tot_dep:+.2f}%)   <- holding would have got this")
    print(f"      + LP skill        {tot_v:+,.1f} SOL   ({100*tot_v/tot_dep:+.2f}%)   <- vs-HODL, the actual edge")
    print(f"    beat HODL in        {beat}/{n} pools ({100*beat/n:.1f}%)")
    print(f"    per-pool vs-HODL    median {100*st.median(per):+.2f}%   p10 {100*per[n//10]:+.2f}%   p90 {100*per[9*n//10]:+.2f}%")
    print(f"    (unweighted mean    {100*sum(per)/n:+.2f}%  -- rule 3: do not rank on this)")
    # Uncovered rows are NOT random: a deposited token with zero withdrawal means price
    # ran clean through the range, i.e. the worst-IL cases. Bound the headline by
    # charging every uncovered row its full realised loss against LP skill (beta = 0).
    unc_rows = [p for p in pools if f(p, "totalDepositSol") > 0 and vs_hodl(p) is None]
    unc_dep  = sum(f(p, "totalDepositSol") for p in unc_rows)
    unc_pnl  = sum(f(p, "pnlSol") for p in unc_rows)
    bounded  = (tot_v + unc_pnl) / (tot_dep + unc_dep)
    print(f"    uncovered rows      {len(unc_rows)}  {unc_dep:,.0f} SOL ({100*unc_dep/(tot_dep+unc_dep):.1f}% of capital)"
          f"  pnl {unc_pnl:+,.1f} ({100*unc_pnl/max(unc_dep,1e-9):+.2f}%)")
    print(f"    LP skill, BOUNDED   {100*bounded:+.2f}%   <- worst case, charging every uncovered row its full loss")
    return dict(n=n, uncovered=uncovered, dep=tot_dep, pnl=tot_pnl, beta=tot_h,
                skill=tot_v, fees=fees, beat_rate=beat/n,
                skill_pct=tot_v/tot_dep, skill_pct_bounded=bounded,
                uncovered_dep=unc_dep, uncovered_pnl=unc_pnl)

if __name__ == "__main__":
    data = json.load(open(SRC))
    out = {k: report(k, ps) for k, ps in data.items()}
    json.dump(out, open("data/vs_hodl.json", "w"), indent=1)
    print("\n  -> data/vs_hodl.json")
