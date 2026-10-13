"""Verify beta_class routing in pool_alert against real mint addresses.

    python3 tools/_test_beta_class.py

Kept in the repo because the class strings are a contract between
stock_pairs.classify_pair (uppercase) and pool_alert's filters (lowercase).
If someone changes one side, this fails.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import pool_alert as pa

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
NVDAx = "Xsc9qvGR1efVDFGLrVsmkzv3qi45LTBjeUKSPmx9qEh"
TSLAx = "XsDoVfqeBukxuZHWhdvWHBhgEHjGNst4MLodqsJHzoB"
AAPLon = "123mYEnRLM2LLYsJW3K6oyYh8uP1fngj732iG638ondo"
PUMP = "9fSncMMvKNcr8T4VBGsk8rBQrKqkRGCFBNWgTTiCpump"

CASES = [
    ({"token_x": {"address": NVDAx, "symbol": "NVDAx"},
      "token_y": {"address": SOL, "symbol": "SOL"}}, "stock"),
    ({"token_x": {"address": AAPLon, "symbol": "AAPLon"},
      "token_y": {"address": USDC, "symbol": "USDC"}}, "stock"),
    ({"token_x": {"address": TSLAx, "symbol": "TSLAx"},
      "token_y": {"address": NVDAx, "symbol": "NVDAx"}}, "stock_meme"),
    ({"token_x": {"address": SOL, "symbol": "SOL"},
      "token_y": {"address": PUMP, "symbol": "PUMP"}}, "meme"),
    # REGRESSION 2026-10-12: KOx is a memecoin, but "KOx" had been written into
    # the equity ticker allowlist from memory. It was classifying three live
    # pools (KOx-SOL, KOx-USDC, OFOO-KOx) as equity. It is now off the list and
    # must classify as a meme -- a memecoin on an `Xs` mint is still a memecoin.
    ({"token_x": {"address": "XsaBXg8dU5cPM6ehmVctMkVqoiRG2ZjMo1cyBJ3AykQ", "symbol": "KOx"},
      "token_y": {"address": SOL, "symbol": "SOL"}}, "meme"),
]

if __name__ == "__main__":
    fails = 0
    for payload, expected in CASES:
        got = pa.beta_class(payload)
        good = got == expected
        fails += not good
        print(f"  {'ok  ' if good else 'FAIL'} expected {expected:<11} got {got}")
    for junk in ({}, {"token_x": None, "token_y": None}, {"token_x": {}, "token_y": {}}):
        got = pa.beta_class(junk)
        if got not in ("meme", "unknown"):
            fails += 1
            print(f"  FAIL malformed payload returned {got!r}")
    print("ALL PASS" if not fails else f"{fails} FAILURES")
    raise SystemExit(1 if fails else 0)