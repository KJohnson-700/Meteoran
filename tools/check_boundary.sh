#!/bin/bash
# Fails if another project's CODE has leaked into Meteoran.
# Meteoran is Meteora DLMM liquidity ONLY. Separate projects, separate data:
#   ~/Documents/mint-doctor   NFT minting / OpenSea
#   ~/Documents/Oracle-3      Polymarket
#   ~/Documents/HyphyLiquid   Hyperliquid derivatives
#
# Scans CODE ONLY. Never data/: Meteora has real tokens called POLYMARKET, ANTHROPIC
# and OPENAI, so a name match inside a pool record is a legitimate pool, not a leak.
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 1
BAD=$(grep -rilE "opensea|fluffberg|gamma-api\.polymarket|hyperliquid\.xyz|clob\.polymarket" \
      --include="*.py" --include="*.sh" tools/ 2>/dev/null \
      | grep -v 'check_boundary.sh')
if [ -n "$BAD" ]; then
  echo "BOUNDARY VIOLATION -- these files belong to another project:"
  echo "$BAD" | sed 's/^/   /'
  echo "   move them: mint-doctor (NFT) | Oracle-3 (Polymarket) | HyphyLiquid (Hyperliquid)"
  exit 1
fi
echo "boundary clean: tools/ is Meteora DLMM only"
