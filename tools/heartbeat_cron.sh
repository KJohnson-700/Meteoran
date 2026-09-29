#!/bin/bash
# Meteoran heartbeat -> one markdown brief into the Hermes vault, hourly.
# Read-only. No keys, places no orders. Pushes to the phone only when a decision
# is actually required (position out of range, or a watcher died).
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 1
/usr/bin/python3 tools/heartbeat.py >> logs/heartbeat.log 2>&1
# refresh the snapshot the browser board reads (an agent still has to push it)
/usr/bin/python3 tools/board_push.py >> logs/heartbeat.log 2>&1
# restart the watchers if they died -- a dead poller is silent, not safe
pgrep -f "tools/pool_alert.py" >/dev/null || \
  nohup /usr/bin/python3 -u tools/pool_alert.py 20 7 20000 >> logs/pool_alert.log 2>&1 &
if [ -s data/operator_wallet.txt ]; then
  pgrep -f "tools/monitor_positions.py" >/dev/null || \
    nohup /usr/bin/python3 -u tools/monitor_positions.py "$(cat data/operator_wallet.txt)" 60 >> logs/monitor.log 2>&1 &
fi
# keep logs bounded
for f in logs/heartbeat.log logs/pool_alert.log logs/monitor.log; do
  [ -f "$f" ] && tail -n 800 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
