#!/usr/bin/env python3
"""Contract tests for the checks. Run: python3 scripts/test_checks.py

Two halves, and the second is the one people skip:

  1. On the positive fixture every check MUST fire.
  2. On the negative fixture every check MUST stay silent.

Without the second half a clean result means nothing -- a probe that cannot fire
reports no findings on a broken file just as happily as on a sound one. Prove the
instrument can pass before trusting a negative.

The third test is the transversal rule, which is the finest judgement in the
method and the easiest to regress.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CODES = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]


def analyse(xml_name):
    xml = os.path.join(ROOT, "fixtures", xml_name)
    with tempfile.TemporaryDirectory() as tmp:
        model = os.path.join(tmp, "model.json")
        out = os.path.join(tmp, "findings.json")
        subprocess.run(
            [sys.executable, os.path.join(HERE, "parse_mspdi.py"), xml, "-o", model],
            check=True, capture_output=True,
        )
        subprocess.run(
            [sys.executable, os.path.join(HERE, "run_checks.py"), model, "--json", out],
            check=True, capture_output=True,
        )
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)


def compare_cycle():
    import compare_snapshots
    import parse_mspdi
    prev = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_prev.xml"))
    curr = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    return compare_snapshots.compare(prev, curr)


def render_sample(cyc):
    import report_html
    return report_html.render_comparison(cyc)


def main() -> int:
    failures = []

    pos = analyse("positive.xml")
    for code in CODES:
        if pos["counts"][code]["distinct_activities"] < 1:
            failures.append(f"positive: {code} did not fire -- the probe is blind to it")

    # Both ends of a violated link must be marked, to agree with the tool's own count.
    for code in ("A1", "A2"):
        c = pos["counts"][code]
        if c["as_successors"] < 1 or c["as_predecessors"] < 1:
            failures.append(f"positive: {code} marked only one end of the link")

    neg = analyse("negative.xml")
    for code in CODES:
        got = neg["counts"][code]["distinct_activities"]
        if got:
            failures.append(f"negative: {code} fired {got} times on a consistent schedule")

    # The transversal rule: a predecessor that is only pending a record (P) is a
    # reporting defect, not a network breach. UID 11 is in P and precedes UID 12,
    # which has started -- that must NOT appear as A1.
    a1_uids = {f["uid"] for f in pos["findings"]["A1"]}
    if 11 in a1_uids or 12 in a1_uids:
        failures.append(
            "positive: the P migration rule regressed -- a pending record was "
            "counted as a network breach, which accuses execution for a "
            "record-keeping problem"
        )

    if not pos["findings"]["P"]:
        failures.append("positive: P did not fire, so the migration rule was never exercised")

    # ---- the comparator, on the cycle pair.
    cyc = compare_cycle()
    readings = {t["reading"] for t in cyc["trend"]}
    if "execution" not in readings:
        failures.append("cycle: no movement was read as execution")
    if "replan" not in readings:
        failures.append("cycle: no movement was read as replan")
    if not cyc["baseline_moved"]:
        failures.append("cycle: a rebased baseline was not detected")
    if not cyc["warnings"]:
        failures.append("cycle: a rebased baseline and a scope change raised no warning")
    if not cyc["unmatched"]["inserted"] or not cyc["unmatched"]["removed"]:
        failures.append("cycle: inserted or removed activities were not detected")
    # The residue must be named, not silently absorbed: scope changed the denominator,
    # so the headline movement is NOT all progress and the report must say so.
    if cyc["movement_unexplained_points"] in (None, 0):
        failures.append(
            "cycle: the unexplained residue was not computed, so a movement that is "
            "partly scope change would be reported as progress"
        )
    aggregates_note = cyc["conventions"]["aggregates"]
    if "called twice" not in aggregates_note:
        failures.append("cycle: the shared-reference convention is no longer declared")

    # ---- the HTML report must be self-contained: no network, ever.
    import re
    html_text = render_sample(cyc)
    external = [u for u in re.findall(r'(?:src|href)=["\'](\S+?)["\']', html_text)
                if u.startswith(("http", "//"))]
    if external:
        failures.append(f"report: external references present, breaks offline use: {external}")

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  * {f}")
        return 1

    print("PASS")
    print(f"  positive: all {len(CODES)} checks fired, both link ends marked")
    print(f"  negative: all {len(CODES)} checks silent on a consistent schedule")
    print("  transversal rule: pending record did not raise a network finding")
    print("  cycle: execution, replan and rebased-baseline all detected; residue named")
    print("  report: no external references, so it works offline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
