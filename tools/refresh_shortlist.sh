#!/bin/bash
# WEEKLY REFRESH -- universe -> screen -> rank -> out-of-sample -> gates -> shortlist.
# Run it, walk away, come back to data/shortlist_final.json and a printed table.
# Every step is resumable; re-running after a crash continues, it does not restart.
#
#   ./tools/refresh_shortlist.sh            full chain (screening step is the slow one)
#   ./tools/refresh_shortlist.sh --fast     skip re-screening, re-gate existing wallets
set -e
cd "$(dirname "$0")/.."

echo "== universe status =="
python3 tools/dlmm_universe.py --stats || true

if [ "$1" != "--fast" ]; then
  echo "== screen accumulated wallets (resumable) ==";  python3 tools/screen_universe.py
  echo "== rule-2 + rhythm filters ==";                 python3 tools/rank_universe.py
  echo "== T1 skill leaderboard ==";                    python3 tools/skill_leaderboard.py
fi

echo "== cache dated pool rows ==";       python3 tools/t2_fetch.py 20
echo "== live selection rule ==";         python3 tools/t2_survivors.py 120
echo "== leak-free per-position A/B ==";  python3 tools/t2_exact.py 120 data/t2_survivors.json
echo "== censoring gate (rule 16) ==";    python3 tools/open_book.py data/t2_survivors.json
echo "== JIT gate (rule 17) ==";          python3 tools/bot_holdtime.py data/t2_survivors.json
echo "== final shortlist ==";             python3 tools/build_shortlist.py

echo
echo "== live confirmation of finalists (vet.py refetches everything) =="
python3 - <<'PY'
import json, subprocess, sys
fin = [x["w"] for x in json.load(open("data/shortlist_final.json")) if x["tier"] == "FINALIST"]
if fin: subprocess.run([sys.executable, "tools/vet.py"] + fin)
PY
