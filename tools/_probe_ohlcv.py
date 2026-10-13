import json
import urllib.request

API = "https://dlmm.datapi.meteora.ag"
UA = {"User-Agent": "Mozilla/5.0"}


def g(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())


d = json.load(open("data/stock_pairs.json"))
p = d["buckets"]["STOCK"][0]
print("pool:", p["name"])
for tf in ("1h", "4h", "24h"):
    try:
        r = g(f"{API}/pools/{p['pool']}/ohlcv?timeframe={tf}")
        rows = r.get("data") or []
        print(f"timeframe={tf}: n={len(rows)} tf_field={r.get('timeframe')}")
        if rows:
            print("   first:", rows[0].get("timestamp_str"), " last:", rows[-1].get("timestamp_str"))
            print("   keys:", sorted(rows[0].keys()))
    except Exception as e:
        print(f"timeframe={tf}: FAIL {type(e).__name__} {e}")