"""Self-containment check for docs/stock-pairs.html.

    python3 tools/stock_report.py && python3 tools/_audit.py

The whole point of this report is that a judge can open one file from the repo
or the raw.githubusercontent URL and it works. That property is easy to break by
accident -- one <link> to a CDN font, one <script src>, and the file still
renders perfectly on the machine that built it. This asserts the property so a
regression shows up as a failed check rather than a blank page on someone's
laptop.

Fails loudly rather than silently: exit 1 on any violation.
"""
from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "docs", "stock-pairs.html")

# The only hosts allowed to appear. Solscan and GitHub are user-facing links
# the reader clicks; a stylesheet or script would have to load without being
# clicked, which is exactly what a judge on bad wifi cannot do.
ALLOWED_HOSTS = ("solscan.io", "github.com")

FAIL = []


def check(name: str, ok: bool, detail: str = "") -> None:
    # Detail explains a FAILURE. Printing it on a pass reads as a warning, which
    # trains the reader to ignore the one line that matters.
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}"
          f"{'  -- ' + detail if detail and not ok else ''}")
    if not ok:
        FAIL.append(name)


def main() -> int:
    if not os.path.exists(HTML):
        print(f"  missing {HTML} -- run: python3 tools/stock_report.py")
        return 1
    s = io.open(HTML, encoding="utf-8").read()

    check("no external stylesheet",
          "<link" not in s.lower(),
          "found <link> -- inline it or the file is not self-contained")
    # An INLINE script is fine and does not break self-containment -- nothing
    # is fetched. What breaks it is a src= pointing at someone else's server.
    check("no external script", " src=" not in s.lower(),
          "found a src= -- inline it or the file is not self-contained")
    check("no @import", "@import" not in s)
    check("no webfont fetch",
          not re.search(r"fonts\.(googleapis|gstatic)", s))
    check("single html document",
          s.lower().count("<!doctype html>") == 1)
    check("utf-8 declared", 'charset="utf-8"' in s.lower())

    urls = sorted(set(re.findall(r'https?://[^"\'< )]+', s)))
    hosts = sorted({re.match(r"https?://([^/]+)", u).group(1).lower()
                    for u in urls})
    check("only known hosts", all(any(h == a or h.endswith("." + a)
                                     for a in ALLOWED_HOSTS) for h in hosts),
          ", ".join(hosts))

    check("has charts", s.count("<svg") >= 2, f"{s.count('<svg')} svg elements")
    # Count data rows, not <tr>: every table also has a header row, and a
    # "close enough" fudge here would silently stop protecting the property.
    body_rows = s.count("<tr") - s.count("<thead>")
    linked = s.count("solscan.io/account/")
    check("has data rows", body_rows > 10, f"{body_rows} data rows")
    check("every row is auditable", linked == body_rows,
          f"{linked} linked of {body_rows} data rows")

    # Template leakage: an f-string brace that failed to interpolate shows up
    # as literal {foo} in the output and reads as broken copy to a judge.
    #
    # Strip <script> as well as <style>. Inline JS legitimately contains braces
    # and the token NaN (isNaN), so scanning it produced false failures that
    # would have trained the reader to ignore this check.
    body = re.sub(r"<style.*?</style>", "", s, flags=re.S)
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    check("no unresolved template braces", "{" not in body,
          next((m.group(0) for m in re.finditer(r"\{[a-zA-Z_][^}]*\}", body)),
               ""))
    for bad in ("nan", "None", "undefined", "NaN"):
        check(f"no {bad!r} leaked", bad not in body)

    print(f"\n  {len(s):,} bytes")
    if FAIL:
        print(f"  {len(FAIL)} check(s) failed")
        return 1
    print("  all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())