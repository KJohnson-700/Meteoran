import json,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
UA="Mozilla/5.0"
def one(line):
    w,c=line.strip().split(",")
    p=subprocess.run(["curl","-s","-m","20","-A",UA,"-H","Accept: application/json",
        f"https://dlmm.datapi.meteora.ag/portfolio/total?user={w}"],
        capture_output=True,text=True)
    try:
        d=json.loads(p.stdout)
        return {"w":w,"open":int(c),
                "pnl_usd":float(d.get("totalPnlUsd") or 0),
                "pnl_sol":float(d.get("totalPnlSol") or 0),
                "pct_usd":float(d.get("totalPnlPctChange") or 0),
                "pct_sol":float(d.get("totalPnlSolPctChange") or 0),
                "closed":int(d.get("totalClosedPositions") or 0)}
    except Exception:
        return None
lines=open("owners.txt").read().strip().split("\n")
with ThreadPoolExecutor(max_workers=24) as ex:
    out=[r for r in ex.map(one,lines) if r]
json.dump(out,open("dlmm_pnl.json","w"))
print(f"  fetched {len(out)} of {len(lines)}")
