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


def analyse_raw(model):
    """Run the checks in-process, for assertions that need the parsed model too."""
    import run_checks
    return run_checks.run(model, run_checks.DEFAULT_THRESHOLD_DAYS,
                          run_checks.DEFAULT_TOLERANCE_DAYS)


def compare_cycle():
    import compare_snapshots
    import parse_mspdi
    prev = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_prev.xml"))
    curr = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    return compare_snapshots.compare(prev, curr)


REVIEW_SECTIONS = [
    "How to read these numbers", "Index", "Progress by", "Starts per month",
    "S-curve from the file", "<polyline",
    "Finish variance against baseline", "Total float", "Problem",
    "To reproduce in the scheduling tool", "Conventions this report used",
]
PT_SECTIONS = [
    "Como ler estes n\u00fameros", "\u00cdndice", "Avan\u00e7o por", "Partidas por m\u00eas",
    "Problema", "Para reproduzir no Project", "Conven\u00e7\u00f5es que este relat\u00f3rio usou",
    "Calend\u00e1rios que carregam o trabalho", "Term\u00f4metro",
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

    # ---- the network rules the in-tool implementation taught, each with a control.
    a1_pairs = {(p["successor_id"], p["predecessor_id"]) for p in pos["pairs"]["A1"]}
    if (15, 14) in a1_pairs:
        failures.append("network: an overlap covered by a lead was accused as A1 -- lag not honoured")
    if (17, 16) in a1_pairs:
        failures.append("network: a pair with both activities complete was counted, against the rule")
    ign = pos.get("ignored", {}).get("A1_both_complete", [])
    if not any(x["successor_id"] == 17 and x["predecessor_id"] == 16 for x in ign):
        failures.append("network: the both-complete inverted pair was not recorded as ignored")
    if (19, 18) not in a1_pairs:
        failures.append("network: a start-to-start lag violation was not detected")
    if (2, 1) not in a1_pairs:
        failures.append("network: the plain finish-to-start breach stopped firing")
    lt = pos["conventions"].get("link_types_evaluated", {})
    if lt.get("SS", 0) < 1:
        failures.append("network: start-to-start links were not counted as evaluated")
    h_why = {f["uid"]: f.get("why") for f in pos["findings"]["H"]}
    if 20 not in h_why or not str(h_why[20]).startswith("start"):
        failures.append("H: a start elapsed with no actual start was not flagged by the start rule")
    if pos["conventions"].get("threshold_basis") != "working_days_task_calendar":
        failures.append("threshold: E and C must be measured in working days of the task calendar")

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

    # ---- custom field discovery. An organisation keeps its meaning in these, and
    # the point is to show someone candidates rather than ask them to recall.
    import custom_fields as cf_mod
    import report_data
    disc = (pm.get("custom_fields") or {})
    if disc.get("declared", 0) < 3:
        failures.append("fields: the fixture's custom field definitions were not read")
    by_alias = {f.get("alias"): f for f in disc.get("fields", [])}
    d_field = by_alias.get("DISCIPLINA")
    if not d_field:
        failures.append("fields: DISCIPLINA was not discovered")
    else:
        if d_field["type"] != "text":
            failures.append(f"fields: DISCIPLINA typed as {d_field['type']} from its values")
        if not d_field["closed_set"]:
            failures.append("fields: a three-value field was not recognised as a closed set")
        if "discipline" not in d_field["suggested_roles"]:
            failures.append("fields: DISCIPLINA did not suggest the discipline role")
    q_field = by_alias.get("QTDE")
    if q_field and q_field["type"] != "number":
        failures.append(f"fields: QTDE typed as {q_field['type']}, not number")

    cands, sparse = cf_mod.interview_candidates(disc)
    if "discipline" not in cands:
        failures.append("fields: no discipline candidate offered for the interview")
    # A justification field filled on almost nothing must surface as a finding, not
    # be silently dropped below a threshold.
    if "justification" not in sparse:
        failures.append(
            "fields: a barely-populated justification field was dropped instead of being "
            "reported as the finding it is"
        )

    # Grouping by a discovered field, by alias, must actually bucket the work.
    res_pos = analyse_raw(pm)
    by_wbs = report_data.build_review(pm, res_pos, grouping="wbs")
    by_disc = report_data.build_review(pm, res_pos, grouping="DISCIPLINA")
    missing_grp = report_data.build_review(pm, res_pos, grouping="NO_SUCH_FIELD")
    if by_disc["meta"]["grouping_mode"] != "custom":
        failures.append("fields: grouping by alias did not resolve to the custom field")
    if len(by_disc["charts"]["by_group"]) < 3:
        failures.append("fields: grouping by discipline produced fewer buckets than values")
    if missing_grp["meta"]["grouping_mode"] != "missing":
        failures.append(
            "fields: a grouping field that does not exist was not reported as missing, so "
            "everything would silently land in one bucket"
        )
    if not by_wbs["meta"].get("grouping_uninformative") and len(by_wbs["charts"]["by_group"]) < 2:
        failures.append("fields: a single-bucket grouping was not flagged as uninformative")

    # ---- earned value reconciled against the file's own figures.
    rc = by_wbs["meta"]["reconciliation"]
    if rc["leaves_compared"] < 5:
        failures.append("reconciliation: the file's BCWP was not read")
    if rc["ahead_of_baseline"] < 1:
        failures.append(
            "reconciliation: work done ahead of its baseline window, which the tool credits "
            "nothing for until the status date reaches the window, was not classified -- it "
            "would surface as an unexplained mismatch or, worse, be hidden"
        )
    if rc["unexplained"] != 0:
        failures.append(f"reconciliation: {rc['unexplained']} unexplained mismatches on a fixture "
                        "built to match to the cent")
    if rc["ev_method"] != "physical":
        failures.append("reconciliation: the declared earned value method was not read")
    # Slot election by coverage: the fixture keeps everything in slot 1, so 1 wins.
    if pm["prevailing_baseline"]["slot"] != "1":
        failures.append("baseline: coverage election picked the wrong slot on the fixture")

    # ---- the S-curve from the file's own phasing. Nothing invented: the per-task
    # sums must equal the totals the file writes, and a non-working day's sentinel
    # must never reach the curve.
    import phasing as phasing_mod
    curve = phasing_mod.build(os.path.join(ROOT, "fixtures", "positive.xml"), None)
    rr = curve["reconciliation"]
    if rr["phasing_sum_equals_cost"] != rr["with_cost"]:
        failures.append(
            f"phasing: baseline-cost blocks sum to the baseline cost on only "
            f"{rr['phasing_sum_equals_cost']} of {rr['with_cost']} tasks"
        )
    if rr["phasing_to_status_equals_bcws"] != rr["tasks"]:
        failures.append(
            f"phasing: blocks up to the status date equal the file's BCWS on only "
            f"{rr['phasing_to_status_equals_bcws']} of {rr['tasks']} tasks"
        )
    T = curve["totals"]
    if T["earned_pct"] is None or T["planned_pct"] is None:
        failures.append("phasing: totals missing")
    # Earned to date must equal the sum of cost x physical over the leaves, which is
    # only true if the 32768 sentinel days were dropped before summing.
    expected = sum(
        ((t.get("baselines") or {}).get("1") or {}).get("cost", 0) * (t.get("physical_percent_complete") or 0) / 100
        for t in pm["tasks"] if not t.get("summary") and t.get("physical_percent_complete")
    )
    if abs(T["earned_to_date"] - expected) > 1.0:
        failures.append(
            f"phasing: earned to date {T['earned_to_date']} != cost x physical {expected:.2f}; "
            "a sentinel day leaked into the curve or the spread was not normalised"
        )
    if T["method_gap_points"] is None:
        failures.append("phasing: the other method's curve was not computed as sensitivity")
    if curve["method"] != "physical":
        failures.append("phasing: the declared earned value method was not read")
    if not curve["periods"] or curve["periods"][-1]["planned_cum_pct"] is None:
        failures.append("phasing: the monthly series is empty or lacks cumulative percent")
    if any(p["earned_cum"] is not None for p in curve["periods"] if p["period"] > "2026-06"):
        failures.append("phasing: earned values appear after the status month")

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
    print("  fields: discovery typed and ranked them; grouping by alias and by a missing name")
    print("  network: lead honoured, both-complete ignored and recorded, SS lag violation caught")
    print("  reconciliation: file BCWP read, ahead-of-baseline classified, no unexplained gap")
    print("  phasing: blocks equal cost and BCWS on every task; sentinel dropped; curve rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
