#!/usr/bin/env python3
"""Regression against a real export, when one is on this machine.

    python3 scripts/test_real.py

Reads the path from `.real-file` at the repository root (gitignored: a real
schedule never enters the repository). If the file is absent the test says so and
exits 0, loudly, rather than passing as if it had run. The expected figures are the
ones measured on 12/09/2026; a change in any of them after a code change is a
regression to explain, not a number to update.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

EXPECTED = {
    "tasks": 6484, "leaves": 5251, "links": 6942, "calendars": 107,
    "A1": 120, "A2": 41, "H": 3, "E": 276, "C": 377, "G": 109, "B": 62, "F": 89, "P": 0,
    "ignored_both_complete": 179,
    "reconciliation_matches": 4676, "reconciliation_compared": 4677, "ahead_of_baseline": 1,
    "phasing_sum_equals_cost": 4677, "phasing_to_status_equals_bcws": 5249,
    "earned_pct": 7.7, "planned_pct": 10.76,
    "quality_Q1": 16, "quality_Q6": 3859, "quality_Q11": 305, "bei": 0.27,
    "milestones_future": 57, "milestones_with_origin": 14,
}


def main() -> int:
    marker = os.path.join(ROOT, ".real-file")
    if not os.path.exists(marker):
        print("SKIPPED: no .real-file at the repository root; the real-export regression did not run")
        return 0
    with open(marker, encoding="utf-8") as fh:
        path = os.path.expanduser(fh.read().strip())
    if not os.path.exists(path):
        print(f"SKIPPED: {path} not found (synced folder placeholder?); regression did not run")
        return 0

    import network_quality
    import parse_mspdi
    import phasing
    import run_checks
    import forensics
    import report_data

    model = parse_mspdi.parse(path)
    res = run_checks.run(model, run_checks.DEFAULT_THRESHOLD_DAYS, run_checks.DEFAULT_TOLERANCE_DAYS)
    curve = phasing.build(path, None)
    qual = network_quality.build(model, path)
    fx = forensics.build(model, res)
    payload = report_data.build_review(model, res, grouping="wbs", lang="en", phasing=curve, quality=qual, forensics=fx)

    got = {
        "tasks": model["counts"]["tasks"], "leaves": model["counts"]["leaves"],
        "links": model["counts"]["links"], "calendars": model["calendars"]["count"],
        **{c: res["counts"][c]["distinct_activities"] for c in run_checks.ORDER},
        "ignored_both_complete": res["conventions"]["both_complete_pairs_ignored"],
        "reconciliation_matches": payload["meta"]["reconciliation"]["matches_to_cent"],
        "reconciliation_compared": payload["meta"]["reconciliation"]["leaves_compared"],
        "ahead_of_baseline": payload["meta"]["reconciliation"]["ahead_of_baseline"],
        "phasing_sum_equals_cost": curve["reconciliation"]["phasing_sum_equals_cost"],
        "phasing_to_status_equals_bcws": curve["reconciliation"]["phasing_to_status_equals_bcws"],
        "earned_pct": curve["totals"]["earned_pct"], "planned_pct": curve["totals"]["planned_pct"],
        "quality_Q1": next(m["count"] for m in qual["metrics"] if m["code"] == "Q1"),
        "quality_Q6": next(m["count"] for m in qual["metrics"] if m["code"] == "Q6"),
        "quality_Q11": next(m["count"] for m in qual["metrics"] if m["code"] == "Q11"),
        "bei": qual["indices"]["bei"],
        "milestones_future": fx["summary"]["milestones"],
        "milestones_with_origin": fx["summary"]["with_origin"],
    }
    diffs = [(k, EXPECTED[k], got.get(k)) for k in EXPECTED if got.get(k) != EXPECTED[k]]
    if diffs:
        print("FAIL: figures changed on the real export")
        for k, e, g in diffs:
            print(f"  {k:<32} expected {e!r} got {g!r}")
        return 1
    print(f"PASS: {len(EXPECTED)} figures unchanged on the real export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
