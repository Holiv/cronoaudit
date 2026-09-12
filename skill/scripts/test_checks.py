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
import re
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


REVIEW_SECTIONS = [
    "How to read these numbers", "Index", "Where the weight sits",
    "Finish variance against baseline", "Total float", "Activity starts per month",
    "How to reproduce it", "Conventions this report used",
]
PT_SECTIONS = [
    "Como ler estes n\u00fameros", "\u00cdndice", "Onde est\u00e1 o peso",
    "Term\u00f4metro", "Conven\u00e7\u00f5es que este relat\u00f3rio usou",
    "Calend\u00e1rios que carregam o trabalho",
]
CYCLE_SECTIONS = [
    "Was it execution, or was it the plan", "RESIDUE", "the baseline itself moved",
    "Where the movement came from", "Scope changes",
]


def render_checks() -> dict:
    """Generate both reports and execute their own renderer."""
    import shutil

    node = shutil.which("node")
    if node is None:
        return {"failures": [], "skipped": True}

    out = {"failures": [], "skipped": False}
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, os.path.join(HERE, "review.py"),
             os.path.join(ROOT, "fixtures", "cycle_prev.xml"),
             os.path.join(ROOT, "fixtures", "cycle_curr.xml"),
             "--outdir", tmp, "--quiet"],
            check=True, capture_output=True,
        )
        pairs = [
            ("cycle_curr-review.html", REVIEW_SECTIONS),
            ("cycle_prev--to--cycle_curr-cycle.html", CYCLE_SECTIONS),
        ]
        # And again in Portuguese, so a missing label is a failing test rather than
        # an English heading appearing in the middle of a Portuguese report.
        pt_dir = os.path.join(tmp, "pt")
        subprocess.run(
            [sys.executable, os.path.join(HERE, "review.py"),
             os.path.join(ROOT, "fixtures", "cycle_curr.xml"),
             "--outdir", pt_dir, "--quiet", "--lang", "pt"],
            check=True, capture_output=True,
        )
        pairs.append((os.path.join("pt", "cycle_curr-review.html"), PT_SECTIONS))
        for name, sections in pairs:
            path = os.path.join(tmp, name)
            if not os.path.exists(path):
                out["failures"].append(f"report: {name} was not produced")
                continue
            p = subprocess.run(
                [node, os.path.join(HERE, "test_render.js"), path, *sections],
                capture_output=True, text=True,
            )
            if p.returncode != 0:
                out["failures"].append(f"report {name}: {p.stderr.strip()}")
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            if "/*DATA*/" in body:
                out["failures"].append(f"report {name}: the data marker was not replaced")
            # No network, ever: it must open from an email attachment on a machine
            # with no connection and look the same.
            external = [
                u for u in re.findall(r'(?:src|href)="([^"]+)"', body)
                if u.startswith(("http", "//"))
            ]
            if external:
                out["failures"].append(
                    f"report {name}: external references break offline use: {external}"
                )
    return out


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

    # ---- calendars. Leaving them out does not approximate the answer, it invents
    # one: a real programme had 107 calendars, most tasks on a 9-hour six-day week
    # while the header said 8 hours over five days.
    import parse_mspdi
    pm = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "positive.xml"))
    cal_block = pm.get("calendars") or {}
    if cal_block.get("count", 0) < 2:
        failures.append("calendars: the fixture's calendars were not parsed")
    in_use = {c["name"]: c for c in cal_block.get("in_use", [])}
    six = in_use.get("Earthworks six-day")
    if not six:
        failures.append("calendars: the six-day calendar is not reported as in use")
    else:
        if six["hours_per_day"] != 9.0:
            failures.append(
                f"calendars: six-day calendar day length read as {six['hours_per_day']}h, "
                "not 9h -- durations on it will convert wrongly"
            )
        if six["working_days_per_week"] != 6:
            failures.append("calendars: the six-day working week was not detected")
        if six["non_working_exceptions"] < 1:
            failures.append("calendars: the holiday exception was not detected")
    # UID 13 sits on the six-day calendar and its duration matches the real working
    # time once the holiday is removed. If it is flagged, the calendar is being
    # ignored -- this is the negative control for the whole calendar path.
    g_uids = {f["uid"] for f in pos["findings"]["G"]}
    if 13 in g_uids:
        failures.append(
            "calendars: a consistent activity on a six-day calendar with a holiday was "
            "flagged as G, so the calendar is not being applied"
        )
    if 8 not in g_uids:
        failures.append("calendars: the genuinely inconsistent duration stopped firing")

    # ---- language. The report follows the schedule, not a flag: the person running
    # the review is often not the person who wrote the file.
    import i18n
    pt_model = {
        "project": {"title": "Duplicação de pista"},
        "calendars": {"in_use": [{"name": "Terraplenagem"}, {"name": "Obras civis"}]},
        "tasks": [
            {"name": "Execução de terraplenagem no trecho sul"},
            {"name": "Implantação de drenagem profunda"},
            {"name": "Concreto para as obras de arte especiais"},
            {"name": "Sinalização horizontal e vertical da faixa"},
        ],
    }
    en_model = {
        "project": {"title": "Highway widening"},
        "calendars": {"in_use": [{"name": "Earthworks"}]},
        "tasks": [
            {"name": "Execution of the earthworks on the southern section"},
            {"name": "Installation of the deep drainage system"},
            {"name": "Concrete for the bridges and structures"},
            {"name": "Signage and lane marking for the works"},
        ],
    }
    got_pt = i18n.detect(pt_model)
    got_en = i18n.detect(en_model)
    if got_pt["lang"] != "pt":
        failures.append(f"language: Portuguese schedule detected as {got_pt['lang']}")
    if got_en["lang"] != "en":
        failures.append(f"language: English schedule detected as {got_en['lang']}")
    thin = i18n.detect({"project": {}, "tasks": [{"name": "X"}]})
    if thin["confidence"] != "low":
        failures.append(
            "language: a file with almost no text did not report low confidence, so a "
            "guess from noise would look like a decision"
        )
    # Every interface string must exist in both languages, or a report silently
    # falls back to English mid-page.
    en_ui = i18n.UI["en"]
    for lang in i18n.UI:
        missing = [k for k in en_ui if k not in i18n.UI[lang]]
        if missing:
            failures.append(f"language: {lang} is missing {len(missing)} labels: {missing[:5]}")
    for lang in i18n.FINDINGS:
        for code in CODES:
            entry = i18n.FINDINGS[lang].get(code)
            if not entry or len(entry) != 5:
                failures.append(f"language: {lang} has no complete text for finding {code}")

    # ---- the report must actually render. A valid file that runs to a blank page
    # is the failure mode this guards; see scripts/test_render.js for the real bug.
    rendered = render_checks()
    failures.extend(rendered["failures"])

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
    if rendered["skipped"]:
        print("  report render: SKIPPED (node not installed) -- the blank-page guard did not run")
    else:
        print("  report render: both reports executed and produced every expected section")
    print("  calendars: 9h six-day week and its holiday applied; consistent task not flagged")
    print("  language: pt and en detected from content; every label present in both")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
