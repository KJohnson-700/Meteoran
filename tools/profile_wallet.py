import json,subprocess,collections,statistics as st
from concurrent.futures import ThreadPoolExecutor
UA="Mozilla/5.0"; API="https://dlmm.datapi.meteora.ag"
W={"CMFkL6Pv":"CMFkL6PvHB8kmU8GgGSfojCo3s3bt7suQ99popyeQj2D",
   "ReNT8Cke":"ReNT8Cke7PygAogBEid1z44aFqhunaQPX7X5mfmj4aY",
   "C7RcE7SW":"C7RcE7SWorDM5DRNdPUxBwCAE9z9p8JGjpkR16F9SYBa"}
def pools(w):
    out=[]
    for pg in range(1,9):
        p=subprocess.run(["curl","-s","-m","25","-A",UA,
            f"{API}/portfolio?user={w}&days_back=365&page={pg}&page_size=100"],
            capture_output=True,text=True)
        try: d=json.loads(p.stdout)
        except Exception: break
        out+=d.get("pools") or []
        if not d.get("hasNext"): break
    return out
res={}
with ThreadPoolExecutor(max_workers=3) as ex:
    for k,ps in zip(W, ex.map(pools, W.values())): res[k]=ps
json.dump(res,open("three_pools.json","w"))
for k,ps in res.items():
    if not ps: print(f"  {k}: no data"); continue
    dep=[float(p.get("totalDepositSol") or 0) for p in ps]
    pnl=[float(p.get("pnlSol") or 0) for p in ps]
    fee=[float(p.get("totalFeeSol") or 0) for p in ps]
    bs=collections.Counter(int(p.get("binStep") or 0) for p in ps)
    bf=collections.Counter(float(p.get("baseFee") or 0) for p in ps)
    tok=collections.Counter(p.get("tokenX") for p in ps)
    quote=collections.Counter(p.get("tokenY") for p in ps)
    wins=sum(1 for x in pnl if x>0)
    d=sorted(dep); pl=sorted(pnl)
    print(f"\n  === {k}  ({len(ps)} pools) ===")
    print(f"    position size SOL   median {st.median(dep):.2f}   p10 {d[len(d)//10]:.2f}   p90 {d[9*len(d)//10]:.2f}   max {max(dep):.1f}")
    print(f"    pnl per pool SOL    median {st.median(pnl):+.3f}   p10 {pl[len(pl)//10]:+.2f}   p90 {pl[9*len(pl)//10]:+.2f}")
    print(f"    win rate            {100*wins/len(ps):.1f}%   total {sum(pnl):+.1f} SOL   fees {sum(fee):+.1f} SOL")
    print(f"    fees / deposit      {100*sum(fee)/max(sum(dep),1e-9):.2f}%")
    print(f"    binStep             {dict(bs.most_common(4))}")
    print(f"    baseFee %           {dict(bf.most_common(4))}")
    print(f"    quote token         {dict(quote.most_common(3))}")
    print(f"    distinct tokens     {len(tok)}   top: {[t for t,_ in tok.most_common(6)]}")
