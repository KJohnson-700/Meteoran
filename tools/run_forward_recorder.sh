#!/bin/bash
# Keeps the forward recorder alive across crashes. It is the only live-data collector in
# the project, so a silent death costs irreplaceable observations -- history can be
# refetched, a missed entry cannot.
cd "$(dirname "$0")/.."
while true; do
  python3 tools/forward_recorder.py "${1:-60}" "${2:-data/shortlist_copyable.json}" \
    >> logs/forward_recorder.log 2>&1
  echo "[$(date -u +%FT%TZ)] recorder exited, restarting in 30s" >> logs/forward_recorder.log
  sleep 30
done
