"""Join the three gate outputs into the final shortlist. Pure disk, no API calls.

Reads   data/t2_exact.json   (leak-free A/B split + concentration, rule 15/13)
        data/open_book.json  (censoring gate, rule 16)
        data/hold_tells.json (JIT gate, rule 17)
Writes  data/shortlist_final.json and prints the table.

Gate thresholds are the ones the 2026-09 shortlist survived -- change them here and
they change everywhere. FINALIST = full evidence bar; WATCH = passes every sign gate
but with a thinner sample, worth re-vetting in a few weeks, not copying yet.
"""
import json, sys

ex   = {r["w"]: r for r in json.load(open("data/t2_exact.json"))}
book = {r["w"]: r for r in json.load(open("data/open_book.json"))}
hold = {r["w"]: r for r in json.load(open("data/hold_tells.json"))}

rows = []
for w, r in ex.items():
    A, B = r.get("A"), r.get("B")
    if not (A and B): continue
    b, h = book.get(w), hold.get(w)
    fails = []
    if A["n"] < 10 or B["n"] < 10:            fails.append("thin")
    if A["pct"] <= 0:                          fails.append("A<=0")
    if B["pct"] <= 0:                          fails.append("B<=0")
    if r.get("B_ex_top3", -1) <= 0:            fails.append("concentrated")
    if b is None:                              fails.append("no open-book row")
    else:
        drag = b["allin_pct"] - b["closed_pct"]
        if b["allin_pct"] <= 0:                fails.append("all-in<=0")
        if drag < -0.01:                       fails.append("censoring drag")
    if h is None:                              fails.append("no hold row")
    elif h["machine"]:                         fails.append("JIT")
    finalist = (not fails and A["n"] >= 100 and B["n"] >= 100
                and 0.5 <= B.get("avg_pos", 0) <= 10
                and r.get("B_ex_top3", 0) >= 0.01)
    rows.append({"w": w, "tier": "FINALIST" if finalist else ("WATCH" if not fails else "CUT"),
                 "fails": fails, "A_pct": A["pct"], "B_pct": B["pct"], "A_n": A["n"],
                 "B_n": B["n"], "beat": B.get("beat"), "avg_pos": B.get("avg_pos"),
                 "ex_top3": r.get("B_ex_top3"), "B_top3_share": r.get("B_top3"),
                 "allin": b["allin_pct"] if b else None,
                 "drag": (b["allin_pct"] - b["closed_pct"]) if b else None,
                 "med_hold_s": h["med_s"] if h else None,
                 "round": h.get("round") if h else None})

order = {"FINALIST": 0, "WATCH": 1, "CUT": 2}
rows.sort(key=lambda x: (order[x["tier"]], -(x["ex_top3"] or -9)))
json.dump(rows, open("data/shortlist_final.json", "w"), indent=1)

print(f"  {'tier':<9}{'wallet':<46}{'A':>7}{'B':>7}{'ex-top3':>8}{'An':>5}{'Bn':>5}"
      f"{'beat':>6}{'SOL/pos':>8}{'all-in':>8}{'hold':>7}  fails")
for x in rows:
    if x["tier"] == "CUT" and len(sys.argv) < 2: continue   # pass any arg to see cuts
    hs = x["med_hold_s"]
    hf = "" if hs is None else (f"{hs/3600:.1f}h" if hs >= 3600 else f"{hs/60:.0f}m")
    print(f"  {x['tier']:<9}{x['w']:<46}{100*x['A_pct']:>+6.1f}%{100*x['B_pct']:>+6.1f}%"
          f"{100*(x['ex_top3'] or 0):>+7.1f}%{x['A_n']:>5}{x['B_n']:>5}"
          f"{100*(x['beat'] or 0):>5.0f}%{x['avg_pos'] or 0:>8.2f}"
          f"{100*(x['allin'] or 0):>+7.1f}%{hf:>7}  {','.join(x['fails'])}")
fin = [x for x in rows if x["tier"] == "FINALIST"]
print(f"\n  {len(fin)} FINALIST, {sum(1 for x in rows if x['tier']=='WATCH')} WATCH,"
      f" {sum(1 for x in rows if x['tier']=='CUT')} CUT -> data/shortlist_final.json")
print("  Final step, ALWAYS: python3 tools/vet.py <finalists> -- live refetch, recency, B as a range")
