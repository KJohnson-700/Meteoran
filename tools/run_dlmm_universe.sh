#!/bin/bash
# Hourly DLMM universe accumulation. One RPC call per hour, ~46MB each.
# Measured turnover: ~160 new wallets/hour, so a week of this reaches ~111k against
# 84.5k from a single snapshot -- and critically it captures the cycle-in/cycle-out
# traders that a point-in-time scan structurally cannot see.
# No trailing sleep in the launcher itself (process-group kill).
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs data
while true; do
  python3 tools/dlmm_universe.py >> logs/dlmm_universe.log 2>&1
  sleep 3600
done
