import json

d = json.load(open("data/stock_pairs.json"))
s, m = d["buckets"]["STOCK"], d["buckets"]["STOCK_MEME"]


def live(rows, key="volume_24h"):
    return [r["apr"] for r in rows if r.get(key, 0) > 0]


def med(xs):
    return sorted(xs)[len(xs) // 2] if xs else 0.0


sl, ml = live(s), live(m)
print("scanned:", f"{d['scanned']:,}")
print(f"STOCK      {len(s):>3} pools  ${sum(r['tvl'] for r in s):,.0f} TVL")
print(f"STOCK_MEME {len(m):>3} pools  ${sum(r['tvl'] for r in m):,.0f} TVL")
print(f"median APR stock       {med(sl):.3f}%  (n={len(sl)})")
print(f"median APR stockxmeme  {med(ml):.3f}%  (n={len(ml)})")
print(f"ratio                  {med(sl)/max(med(ml),1e-9):.1f}x")
print("\ntop 6 by TVL:")
for r in sorted(s + m, key=lambda r: -r["tvl"])[:6]:
    print(f"  {r['name']:<18} ${r['tvl']:>10,.0f}  {r['apr']:>6.3f}%")