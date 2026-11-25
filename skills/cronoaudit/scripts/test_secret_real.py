#!/usr/bin/env python3
"""Secret mode on a real export, when one is on this machine.

    python3 scripts/test_secret_real.py

Reads the path from `.real-file` at the repository root, as test_real.py does. Runs
the same round trip and leak test as test_checks.py (secret_roundtrip), in a
temporary folder that is deleted at the end, vault included, and prints ONLY pass
or fail and counts: never a name, a value, a date or a path of the file. An error
inside prints its type only, because a traceback can carry a task name.
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)


def main() -> int:
    marker = os.path.join(ROOT, ".real-file")
    if not os.path.exists(marker):
        print("SKIPPED: no .real-file at the repository root; the secret-mode real test did not run")
        return 0
    with open(marker, encoding="utf-8") as fh:
        path = os.path.expanduser(fh.read().strip())
    if not os.path.exists(path):
        print("SKIPPED: the real file is not reachable; the secret-mode real test did not run")
        return 0
    try:
        import test_checks
        with tempfile.TemporaryDirectory() as tmp:
            r = test_checks.secret_roundtrip([path], tmp, redact=True)
    except Exception as exc:
        print(f"FAIL: the run raised {type(exc).__name__}")
        return 1
    s = r["stats"]
    print(f"{'FAIL' if r['failures'] else 'PASS'}: secret mode on the real export")
    print(f"  equality: {s['sidecars']} sidecars and {s['reports']} report(s) decoded equal to free mode "
          f"({s['values_equal']} report values)")
    print(f"  leak test: {s['texts_checked']} texts and {s['money_checked']} money forms looked for; "
          f"{s['leak_values']} found, {s['leak_hits']} date-shape or path occurrences")
    ex = s.get("excused") or {}
    print(f"  excused as coincidence: {ex.get('vocabulary', 0)} program word(s), "
          f"{ex.get('coded figure', 0)} coded figure(s)")
    for kind, length, where in s.get("hit_detail") or []:
        # Kind, length and surface only. Surfaces are the work folder's neutral file
        # names (schedule-*), stdout, stderr or finish: none carries the file's identity.
        print(f"  - hit: {kind}, {length} characters, in {where}")
    for f in r["failures"]:
        print(f"  * {f}")
    return 1 if r["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
