# PRE-SUBMIT CHECK — one pass, ~15 minutes

**For another agent or a fresh chat. Deadline 2026-10-13 06:59 UTC.**

Goal: verify everything that goes into the form is true and current. **Do not
add claims, do not improve copy, do not write new findings.** This is a check
pass. The only edits permitted are ones that make an existing claim match the
data.

---

## 0. The one thing that is not answerable from the repo

The submission form has a yes/no field: **has this already been submitted to
Colosseum?** The answer is unknown and is not recorded anywhere in the repo.
Ask the user. Do not guess, and do not submit until they answer.

---

## 1. Run the check

```bash
cd meteoran
git pull
python3 tools/stock_pairs.py 60     # ~4 min, re-pulls from the live API
python3 tools/stock_report.py      # regenerates docs/stock-pairs.html
python3 tools/_audit.py            # MUST print "all checks passed"
python3 tools/_summary.py --sync   # rewrites the live-figures paragraph
```

`_audit.py` is the gate. It fails the build on: external stylesheet, external
script `src=`, `@import`, webfont fetch, unescaped template braces, `nan` /
`None` / `NaN` leaking into the page, missing charts, and any data row that
isn't linked to Solscan.

---

## 2. Every claim in SUBMISSION.md, and how to check it

| claim | source | how to verify |
|---|---|---|
| 111,838 closed positions | `README.md` | grep it |
| fees covered IL 3.74x | `README.md` / `THESIS.md` | grep it |
| 24,000 pools scanned | `data/stock_pairs.json` → `scanned` | `python tools/_summary.py` |
| 37 rankable / 23 stock / 14 stock×meme | generated | `_summary.py --sync` |
| median 1h yields | generated | `_summary.py --sync` |
| $1,000 TVL floor | `tools/stock_report.py` → `MIN_TVL` | read the constant |
| six windows 30m–24h | `stock_pairs.py` → `WINDOWS` | read the constant |
| ranked on 1h | `stock_report.py` → `RANK_WINDOW` | read the constant |
| nine gates in the alerter | `tools/pool_alert.py` | count them |
| OHLCV caps at 10 candles | `tools/session_boundary.py` | read it — this is a **measured** capability limit, not an estimate |
| KOx allowlist bug, 3 pools misclassified | `tools/_test_beta_class.py` | run it |

Anything in `SUBMISSION.md` marked `<!-- live-figures -->` is generated. Never
edit it by hand; edit the generator and re-run `--sync`.

---

## 3. The three traps that have already bitten

**Numbers drift every 30 minutes.** The scheduled Action re-commits a fresh
pull. Anything you checked 40 minutes ago may be stale. Re-run section 1 last,
immediately before pasting.

**A ratio with a zero denominator is not a number.** The median stock×memecoin
1h yield is frequently exactly `0.0000%` (8 of 14 pools were at zero on the
last pull). `_summary.py` now prints `ratio undefined (denominator median is
0)` and the generated paragraph says so in words. **If you see a bare ratio
like "11x" anywhere, it is stale and wrong — find and remove it.** The 11x
figure was real once, on the old 24h median, and it died when the ranking
moved to the 1h window.

**"APR" is the wrong word.** Meteora's `apr` field is exactly
`fee_tvl_ratio["24h"]` — a 24-hour fee/TVL percentage with **no annualisation**.
Calling it APR implies a ~365x extrapolation the tool never performed. The page
and the script say "yield". Keep it that way.

---

## 4. Live links — check all three return 200

```
https://kjohnson-700.github.io/Meteoran/stock-pairs.html
https://github.com/KJohnson-700/Meteoran
https://raw.githubusercontent.com/KJohnson-700/Meteoran/main/docs/stock-pairs.html
```

GitHub Pages can lag a commit by a minute or two. If Pages is stale but raw is
current, wait — do not re-render to "fix" it.

---

## 5. The page makes no claim — verify it still doesn't

The page reports data, method, and limits. It must not rank one class against
another, must not declare a winner, and must not tell a reader a class is bad.
`tools/_audit_copy.py` scans the rendered HTML for verdict language and prints
what it finds.

Run it. Every hit should be either the per-class "best payer" line (the tool
doing its job — allowed) or a table header. Anything reading as an editorial
verdict is a regression.

---

## 6. Mandatory fields on the form

| field | value |
|---|---|
| Project name | Meteoran |
| Project description | `SUBMISSION.md` → Project Description |
| GitHub link | https://github.com/KJohnson-700/Meteoran (**mandatory**) |
| Pitch deck or Loom | **mandatory** — user records it, `Win + Alt + R` |
| Website | https://kjohnson-700.github.io/Meteoran/stock-pairs.html |

If the entry is closed-source to anyone, add GitHub ID `dannxbt` with read
access. The repo is public, so this is likely unnecessary — confirm, don't
assume.

---

## 7. Final read-through

Read the Project Description top to bottom and ask of every sentence: *can this
be defended from the repo?* If not, cut it. Do not soften it into vagueness —
cut it.

Specifically, confirm the description does **not**:
- quote a ratio between the two pool classes
- quote a fixed percentage of "corrupt" API rows (it moves between pulls)
- claim impermanent loss, returns, or predictive power
- describe the session-boundary study as anything other than not built
- imply the tool places trades or needs a wallet

---

## 8. What is deliberately not built

Say so if asked; do not imply otherwise.

- **Session-boundary study** — OHLCV caps at 10 candles per call, so it cannot
  be done from one pull.
- **No time series** — this is a cross-section from one pull.
- **No wallet-level skill measurement on equity pools.**
- **The alerter is not hosted.** It runs on the operator's machine because a
  public push channel would be a different, worse product. The report *is*
  live.

---

## Repo map, if you need more

| file | what it is |
|---|---|
| `THESIS.md` | the original memecoin research and why equity is the open question |
| `CLAUDE.md` | rules 1–27, including the corrupt-data and wallet-enumeration limits |
| `HANDOVER.md` | operator's live capital/position doc — **do not edit** |
| `SUBMISSION.md` | form-ready copy; `live-figures` block is generated |
| `LOOM-SCRIPT.md` | recording script for the mandatory video |
| `DBC-PITCH.md` | long pitch deck source material |
| `tools/stock_pairs.py` | pull + classify + capture windows |
| `tools/stock_report.py` | render `docs/stock-pairs.html` |
| `tools/_audit.py` | the gate — must pass |
| `tools/_audit_copy.py` | scans for verdict language on the page |
| `tools/_summary.py --sync` | regenerates the submission figures |

---

## Report back

State plainly: which of sections 1–7 passed, which failed, what you changed,
and anything you could not verify. If everything passed, say so in one line.