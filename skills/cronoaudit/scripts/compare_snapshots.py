#!/usr/bin/env python3
"""Compare two snapshots of the SAME schedule -- previous delivery against current.

    python3 parse_mspdi.py previous.xml -o prev.json
    python3 parse_mspdi.py current.xml  -o curr.json
    python3 compare_snapshots.py prev.json curr.json --json cycle.json

The question is not "is this file consistent" (run_checks.py answers that). It is
"what moved since last time, and was it the works that moved or the plan?"

Two rules govern this file:

* Both snapshots' aggregate figures come from ONE function called twice. Do not
  verify that the two halves agree -- construct them so they cannot disagree. Two
  code paths pass their comparison test until somebody edits one of them.
* A changed baseline is a finding ABOUT THE REPORT, not about performance. Every
  deviation that straddles the change is measured against two references.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

# Run by path from anywhere, on any interpreter: an isolated Python (-I), and the
# embeddable Windows package with its ._pth file, do not put the script's own
# folder on sys.path, so the sibling modules below would not be found.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import calendars as cal_mod
import forensics as forensics_mod
import network_quality as quality_mod

EPS = 1e-4
# How many rows the "float fell the most" ranking keeps. The count of every
# activity that lost float is reported beside it, so the cut hides nothing.
FLOAT_TOP_N = 25
# A float or duration change below this many working days is conversion noise.
MIN_DAYS = 0.05
# Lag formats the tool writes for a percentage lag; the stored value is then the
# percentage itself, not tenths of a minute.
PERCENT_LAG_FORMATS = {"19", "20", "51", "52"}
CONSTRAINT_CODES = {0: "ASAP", 1: "ALAP", 2: "MSO", 3: "MFO",
                    4: "SNET", 5: "SNLT", 6: "FNET", 7: "FNLT"}
DATED_CONSTRAINTS = {2, 3, 4, 5, 6, 7}


def dt(v):
    return datetime.fromisoformat(v) if v else None


def days_between(a, b):
    a, b = dt(a), dt(b)
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 86400.0, 1)


def considered(t) -> bool:
    """Leaf, active, not external, not a milestone.

    Summaries would double-count their children. Milestones have no duration, so
    they distort every rate -- and their cost legitimately sits outside a phased
    curve, which is a separate finding rather than an input here.
    """
    return (
        not t.get("summary")
        and t.get("active") is not False
        and not t.get("external")
        and not t.get("milestone")
    )


def leaf(t) -> bool:
    """Leaf, active, not external -- milestones INCLUDED.

    The population for everything that is about logic and record rather than
    about weight: a milestone has no duration to distort a rate here, and a
    critical milestone or a rewritten actual date on one is exactly as much a
    finding as on any other row.
    """
    return not t.get("summary") and t.get("active") is not False and not t.get("external")


def zero(v, digits=4):
    """Round, and never return negative zero: "-0,000" in a report is noise that
    reads as a sign."""
    if v is None:
        return None
    r = round(v, digits)
    return 0.0 if r == 0 else r


class Basis:
    """The conversion basis of ONE snapshot: each activity's own working day."""

    def __init__(self, model: dict):
        blob = model.get("calendars") or {}
        self.cals = cal_mod.from_dict(blob.get("definitions"))
        self.default = blob.get("default_uid")
        self.fallback = (model.get("units") or {}).get("minutes_per_day") or 480.0

    def day_minutes(self, t) -> float:
        c = cal_mod.resolve(self.cals, t.get("calendar_uid"), self.default)
        return (c.day_minutes if c else None) or self.fallback

    def days(self, t, minutes):
        return None if minutes is None else round(minutes / self.day_minutes(t), 2)


def project_finish(model: dict) -> dict:
    """Where ONE snapshot says the project ends, and what holds that date.

    Called once per snapshot, like `snapshot_aggregate`, so the two halves cannot
    have been produced by different rules.

    The driving activity is APPROXIMATED, and declared as such: the open activity
    that finishes last, walked back through the predecessor whose link lands
    latest on each start (the same walk the forensics use), stopping at the first
    row that is not a milestone. The network is not recalculated here; the walk
    reads the dates the tool left in the file.
    """
    basis = Basis(model)
    by_uid = {t["uid"]: t for t in model["tasks"]}
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    pool = [t for t in model["tasks"] if leaf(t) and t.get("finish")]
    latest = max((t["finish"] for t in pool), default=None)
    header = model["project"].get("finish")
    out = {
        "finish": header or latest,
        "finish_basis": "project header" if header else "latest activity finish",
        "latest_activity_finish": latest,
        "end": None, "driver": None, "chain": [],
        "driver_basis": "approximated: last-finishing open activity, walked back through "
                        "the predecessor whose link lands latest; no network recalculation",
    }
    candidates = [t for t in pool if not t.get("actual_finish")] or pool
    if not candidates:
        return out
    # Ties go to the critical row, then to a milestone (the closing milestone and
    # the activity that feeds it finish at the same instant), then to the last row.
    end = max(candidates, key=lambda t: (t["finish"], bool(t.get("critical")),
                                         bool(t.get("milestone")), t["id"] or 0))
    chain = forensics_mod.driving_chain(end, by_uid, basis.cals, basis.default, slot)
    driver = next((by_uid[n["uid"]] for n in chain if not by_uid[n["uid"]].get("milestone")), end)

    def brief(t):
        return {"uid": t["uid"], "id": t["id"], "name": t["name"], "finish": t.get("finish"),
                "critical": t.get("critical"), "milestone": bool(t.get("milestone")),
                "total_float_days": basis.days(t, t.get("total_slack_minutes"))}

    out["end"] = brief(end)
    out["driver"] = brief(driver)
    out["chain"] = [{"uid": n["uid"], "id": n["id"], "name": n["name"], "finish": n["finish"],
                     "critical": n["critical"], "via": n.get("via"),
                     "started": n["started"]} for n in chain[:15]]
    return out


def critical_basis(model: dict) -> str:
    """Which criterion this snapshot can be read by.

    The tool's own Critical flag when the file carries it; total float at or
    below zero otherwise. The flag follows the tool's configured threshold, which
    is the reading the planner sees on screen, so it wins when present.
    """
    return "flag" if any(t.get("critical") is not None for t in model["tasks"] if leaf(t)) else "float"


def is_critical(t, basis: str) -> bool:
    if t.get("actual_finish"):
        return False  # finished work is on no path any more
    if basis == "flag":
        return bool(t.get("critical"))
    sl = t.get("total_slack_minutes")
    return sl is not None and sl <= 0


def critical_path_changes(pairs, inserted, prev, curr, bp: Basis, bc: Basis) -> dict:
    basis_p, basis_c = critical_basis(prev), critical_basis(curr)
    entered, left, fell = [], [], []
    for p, c, _ in pairs:
        if not leaf(c):
            continue
        fb = bp.days(p, p.get("total_slack_minutes"))
        fa = bc.days(c, c.get("total_slack_minutes"))
        was, now = is_critical(p, basis_p), is_critical(c, basis_c)
        row = {"uid": c["uid"], "id": c["id"], "name": c["name"],
               "float_before_days": fb, "float_after_days": fa,
               "finish_before": p.get("finish"), "finish_after": c.get("finish")}
        if now and not was and not p.get("actual_finish"):
            entered.append(row)
        elif was and not now:
            left.append({**row, "completed": bool(c.get("actual_finish"))})
        if not c.get("actual_finish") and fb is not None and fa is not None and fb - fa >= 1:
            fell.append({**row, "float_fell_days": round(fb - fa, 2)})
    entered.sort(key=lambda r: (r["finish_after"] or "", r["id"] or 0))
    left.sort(key=lambda r: (r["completed"], r["finish_after"] or "", r["id"] or 0))
    fell.sort(key=lambda r: (-r["float_fell_days"], r["id"] or 0))
    return {
        "criterion_previous": basis_p, "criterion_current": basis_c,
        "critical_previous": sum(1 for t in prev["tasks"] if leaf(t) and is_critical(t, basis_p)),
        "critical_current": sum(1 for t in curr["tasks"] if leaf(t) and is_critical(t, basis_c)),
        "entered": entered, "left": left,
        "left_completed": sum(1 for r in left if r["completed"]),
        "inserted_critical": sum(1 for t in inserted if is_critical(t, basis_c)),
        "float_fell_count": len(fell), "float_fell_top": fell[:FLOAT_TOP_N],
        "float_fell_min_days": 1,
    }


def lag_of(link, successor, basis: Basis) -> dict:
    """A lag in the unit a person reads: working days of the successor's own
    calendar, or the percentage when the tool stored one."""
    raw = link.get("lag_minutes") or 0.0
    if str(link.get("lag_format")) in PERCENT_LAG_FORMATS:
        return {"value": zero(raw * 10.0, 2), "unit": "percent"}
    return {"value": zero(raw / basis.day_minutes(successor), 2), "unit": "days"}


def logic_changes(pairs, inserted, removed_all, prev, curr, bp: Basis, bc: Basis) -> dict:
    """Links and constraints, compared on activities present in BOTH snapshots.

    A link is identified by its two ends, each resolved through the same match
    as the activities (UID, then name plus WBS path). A link with an end that was
    inserted or removed is a consequence of the scope change, already reported
    there, so it is counted apart and not listed as edited logic.
    """
    to_curr = {p["uid"]: c["uid"] for p, c, _ in pairs}
    matched_curr = set(to_curr.values())
    curr_by = {t["uid"]: t for t in curr["tasks"]}
    added, removed, lag_changed, type_changed = [], [], [], []
    scope_links = 0
    for p, c, _ in pairs:
        before, after = {}, {}
        for l in p.get("predecessors") or []:
            target = to_curr.get(l.get("predecessor_uid"))
            if target is None:
                scope_links += 1
            else:
                before.setdefault(target, l)
        for l in c.get("predecessors") or []:
            if l.get("predecessor_uid") in matched_curr:
                after.setdefault(l["predecessor_uid"], l)
            else:
                scope_links += 1
        for pu in sorted(set(before) | set(after)):
            pred = curr_by[pu]
            lb, la = before.get(pu), after.get(pu)
            row = {"uid": c["uid"], "id": c["id"], "name": c["name"],
                   "predecessor_uid": pu, "predecessor_id": pred["id"],
                   "predecessor_name": pred["name"],
                   "type_before": lb["type"] if lb else None,
                   "type_after": la["type"] if la else None,
                   "lag_before": lag_of(lb, p, bp) if lb else None,
                   "lag_after": lag_of(la, c, bc) if la else None}
            if lb is None:
                added.append(row)
            elif la is None:
                removed.append(row)
            else:
                if lb["type"] != la["type"]:
                    type_changed.append(row)
                if row["lag_before"] != row["lag_after"]:
                    lag_changed.append(row)
    # Links hanging on an inserted or removed successor are scope as well.
    scope_links += sum(len(t.get("predecessors") or []) for t in inserted)
    scope_links += sum(len(t.get("predecessors") or []) for t in removed_all)

    c_added, c_removed, c_changed = [], [], []
    for p, c, _ in pairs:
        if not leaf(c) or c.get("actual_finish"):
            continue  # a constraint on finished work constrains nothing
        tb, ta = p.get("constraint_type") or 0, c.get("constraint_type") or 0
        db = p.get("constraint_date") if tb in DATED_CONSTRAINTS else None
        da = c.get("constraint_date") if ta in DATED_CONSTRAINTS else None
        if tb == ta and db == da:
            continue
        row = {"uid": c["uid"], "id": c["id"], "name": c["name"],
               "type_before": CONSTRAINT_CODES.get(tb, str(tb)),
               "type_after": CONSTRAINT_CODES.get(ta, str(ta)),
               "date_before": db, "date_after": da}
        if tb == 0:
            c_added.append(row)
        elif ta == 0:
            c_removed.append(row)
        else:
            c_changed.append(row)
    return {
        "links_added": added, "links_removed": removed,
        "lag_changed": lag_changed, "type_changed": type_changed,
        "links_from_scope": scope_links,
        "constraints_added": c_added, "constraints_removed": c_removed,
        "constraints_changed": c_changed,
        "constraint_population": "leaf, active, non-external, not finished in the current snapshot",
    }


def duration_changes(pairs, bp: Basis, bc: Basis) -> list:
    """Duration edited on work that has not started in either snapshot.

    With no actual start on either side nothing was executed, so a different
    duration is the plan being rewritten -- the remaining work of the contract
    changed by a keystroke, not by the works.
    """
    out = []
    for p, c, _ in pairs:
        if not considered(c) or p.get("actual_start") or c.get("actual_start"):
            continue
        dp, dc = p.get("duration_minutes"), c.get("duration_minutes")
        if dp is None or dc is None:
            continue
        before, after = bp.days(p, dp), bc.days(c, dc)
        if abs(dc - dp) < 1 or abs(after - before) < MIN_DAYS:
            continue
        out.append({"uid": c["uid"], "id": c["id"], "name": c["name"],
                    "duration_before_days": before, "duration_after_days": after,
                    "delta_days": round(after - before, 2),
                    "finish_before": p.get("finish"), "finish_after": c.get("finish")})
    out.sort(key=lambda r: (-abs(r["delta_days"]), r["id"] or 0))
    return out


def past_rewritten(pairs) -> dict:
    """What was already recorded as done, and reads differently now.

    An actual date is a record of something that happened; a percent complete is
    a measurement already reported. Neither should move backwards between two
    deliveries without a stated correction. When one does, every figure of the
    previous cycle that rested on it was reported on a past that no longer
    exists -- silently, because nothing in either file says so.
    """
    starts, finishes, percents = [], [], []
    touched = set()
    for p, c, _ in pairs:
        if not leaf(c):
            continue
        base = {"uid": c["uid"], "id": c["id"], "name": c["name"]}
        for key, bucket in (("actual_start", starts), ("actual_finish", finishes)):
            b, a = p.get(key), c.get(key)
            if not b or b == a:
                continue
            bucket.append({**base, "before": b, "after": a, "removed": a is None,
                           "moved_days": days_between(b, a) if a else None,
                           "same_day": bool(a) and a[:10] == b[:10]})
            touched.add(c["uid"])
        # One row per activity: the physical percent first, because it is the one
        # the earned value reads; the duration percent only when the physical one
        # did not go down (or is not there to compare).
        for key, label in (("physical_percent_complete", "physical"),
                           ("percent_complete", "duration")):
            b, a = p.get(key), c.get(key)
            if b is None or a is None or a >= b - EPS:
                continue
            percents.append({**base, "field": label, "before": b, "after": a,
                             "delta_points": round(a - b, 2)})
            touched.add(c["uid"])
            break
    starts.sort(key=lambda r: (r["same_day"], r["id"] or 0))
    finishes.sort(key=lambda r: (r["same_day"], r["id"] or 0))
    percents.sort(key=lambda r: (r["delta_points"], r["id"] or 0))
    return {
        "activities": len(touched),
        "actual_start": starts, "actual_finish": finishes, "percent_decreased": percents,
        "actual_removed": sum(1 for r in starts + finishes if r["removed"]),
        "time_of_day_only": sum(1 for r in starts + finishes if r["same_day"]),
        "population": "leaf, active, non-external, matched in both snapshots; milestones included",
    }


def quality_side_by_side(prev: dict, curr: dict) -> dict:
    """The network-quality metrics of both snapshots, by the one implementation.

    `network_quality.build` is called twice; nothing is recomputed here. The
    resource metric (Q10) needs the XML itself, so it is only computable when the
    snapshot came straight from a file.
    """
    def xml_of(model):
        path = model.get("source_path")
        return path if (path and path.lower().endswith(".xml") and os.path.exists(path)) else None

    qp, qc = quality_mod.build(prev, xml_of(prev)), quality_mod.build(curr, xml_of(curr))
    by_code = {m["code"]: m for m in qp["metrics"]}

    def side(m):
        return {k: m[k] for k in ("count", "population", "share_pct", "status")}

    rows = []
    for m in qc["metrics"]:
        o = by_code.get(m["code"])
        if o is None:
            continue
        change = None
        a, b = o.get("share_pct"), m.get("share_pct")
        if a is not None and b is not None and m["population"] and o["population"]:
            worse = (b < a) if m.get("direction") == "min" else (b > a)
            change = "unchanged" if abs(b - a) < 0.005 else ("worsened" if worse else "improved")
        rows.append({
            "code": m["code"], "threshold_pct": m.get("threshold_pct"),
            "direction": m.get("direction"),
            "previous": side(o), "current": side(m),
            "count_delta": m["count"] - o["count"],
            "share_delta_points": zero(b - a, 2) if (a is not None and b is not None) else None,
            "change": change,
            "crossed": (f"{o['status']}->{m['status']}"
                        if o.get("status") and m.get("status") and o["status"] != m["status"]
                        else None),
        })
    keys = ("bei", "bei_due", "cpli", "cpli_meaningful", "critical_activities")
    return {
        "metrics": rows,
        "indices": {"previous": {k: qp["indices"].get(k) for k in keys},
                    "current": {k: qc["indices"].get(k) for k in keys}},
        "population": {"previous": qp["population"], "current": qc["population"]},
        "provenance": qc["provenance"],
    }


def snapshot_aggregate(model: dict) -> dict:
    """The aggregate figures for ONE snapshot.

    Called once per snapshot, from the same code, so the previous cycle's number
    cannot have been produced by a different rule from the current one. That is
    the cheapest available guarantee that both halves of the comparison share a
    reference -- and the difference between two figures built by two rules is a
    datum artefact that reads as performance.
    """
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    planned = earned = 0.0
    leaves = 0
    for t in model["tasks"]:
        if not considered(t):
            continue
        bl = (t.get("baselines") or {}).get(slot) if slot else None
        bcost = (bl or {}).get("cost") or 0.0
        if bcost <= 0:
            continue
        leaves += 1
        phys = t.get("physical_percent_complete")
        if phys is None:
            phys = t.get("percent_complete") or 0.0
        planned += bcost
        earned += bcost * (phys / 100.0)
    return {
        "baseline_slot": slot,
        "budget_at_completion": round(planned, 2),
        "earned": round(earned, 2),
        "percent_earned": round(earned / planned * 100, 4) if planned else None,
        "leaves_with_baseline_cost": leaves,
        "status_date": model["project"].get("status_date"),
        "percent_source": "physical percent complete, falling back to percent complete",
    }


def index_by_name_wbs(tasks) -> dict:
    idx = {}
    for t in tasks:
        key = f"{t.get('name')}|{t.get('wbs')}"
        idx.setdefault(key, t)
    return idx


def match(prev_tasks, curr_tasks):
    """Two-step cascade, then two classes -- and only two.

    1. the stable unique identifier
    2. failing that, name plus WBS path

    A renamed activity that also moved branch is indistinguishable from a removal
    plus an insertion. Inventing a third class would assert something unverifiable,
    so the unmatched count is reported as a number a person must judge.

    The phantom row representing an inserted subproject carries a FILE-LOCAL
    identifier: matching across files on it resolves to the wrong pair rather than
    to nothing, which is worse than failing. Those rows are excluded by
    `considered` along with other summaries.
    """
    by_uid = {t["uid"]: t for t in prev_tasks}
    by_name = index_by_name_wbs(prev_tasks)
    pairs, inserted, used = [], [], set()

    for c in curr_tasks:
        p = by_uid.get(c["uid"])
        how = "uid"
        if p is None:
            p = by_name.get(f"{c.get('name')}|{c.get('wbs')}")
            how = "name+wbs"
        if p is None:
            if considered(c):
                inserted.append(c)
            continue
        used.add(p["uid"])
        pairs.append((p, c, how))

    removed = [p for p in prev_tasks if p["uid"] not in used and considered(p)]
    return pairs, inserted, removed


def compare(prev: dict, curr: dict) -> dict:
    agg_prev = snapshot_aggregate(prev)
    agg_curr = snapshot_aggregate(curr)
    pairs, inserted, removed = match(prev["tasks"], curr["tasks"])

    slot = agg_curr["baseline_slot"]
    trend, baseline_moved, decomposition = [], [], []

    for p, c, how in pairs:
        if not considered(c):
            continue

        moved_start = days_between(p.get("start"), c.get("start"))
        moved_finish = days_between(p.get("finish"), c.get("finish"))
        if (moved_start or 0) or (moved_finish or 0):
            has_actuals = bool(c.get("actual_start") or c.get("actual_finish"))
            trend.append({
                "uid": c["uid"], "id": c["id"], "name": c["name"], "matched_by": how,
                "start_moved_days": moved_start, "finish_moved_days": moved_finish,
                "actuals_present": has_actuals,
                # The discriminator. Dates moving with actuals behind them is the
                # works behaving differently; dates moving with none is a rewritten
                # forecast. Both are legitimate; only one is execution.
                "reading": "execution" if has_actuals else "replan",
            })

        bp = (p.get("baselines") or {}).get(slot) or {}
        bc = (c.get("baselines") or {}).get(slot) or {}
        bs = days_between(bp.get("start"), bc.get("start"))
        bf = days_between(bp.get("finish"), bc.get("finish"))
        if (bs or 0) or (bf or 0):
            baseline_moved.append({
                "uid": c["uid"], "id": c["id"], "name": c["name"],
                "baseline_start_moved_days": bs, "baseline_finish_moved_days": bf,
                "slot": slot,
            })

    # Weight-relative decomposition against the CURRENT snapshot's budget, so the
    # contributions sum to the aggregate deviation instead of merely correlating
    # with it. State the denominator: a decomposition against a different one is
    # not comparable with last cycle's.
    denom = agg_curr["budget_at_completion"]
    total = 0.0
    if denom:
        for p, c, _ in pairs:
            if not considered(c):
                continue
            bc = (c.get("baselines") or {}).get(slot) or {}
            bcost = bc.get("cost") or 0.0
            if bcost <= 0:
                continue
            phys_c = c.get("physical_percent_complete")
            if phys_c is None:
                phys_c = c.get("percent_complete") or 0.0
            phys_p = p.get("physical_percent_complete")
            if phys_p is None:
                phys_p = p.get("percent_complete") or 0.0
            contribution = bcost * (phys_c - phys_p) / 100.0 / denom * 100.0
            if abs(contribution) >= EPS:
                total += contribution
                decomposition.append({
                    "uid": c["uid"], "id": c["id"], "name": c["name"],
                    "wbs": c.get("wbs"),
                    "percent_previous": phys_p, "percent_current": phys_c,
                    "baseline_cost": bcost,
                    "contribution_points": round(contribution, 4),
                })
    decomposition.sort(key=lambda d: abs(d["contribution_points"]), reverse=True)

    # Structured twins of the warnings below, so a report can say them in its own
    # language; the English sentences stay as the stable, quotable form.
    warning_codes = []
    warnings = []
    if baseline_moved:
        warning_codes.append({"code": "baseline_moved", "n": len(baseline_moved)})
        warnings.append(
            f"The baseline moved on {len(baseline_moved)} activities between these two "
            "snapshots. Your comparison basis changed underneath the comparison: every "
            "deviation straddling the change is measured against two references. Report "
            "this as a finding about the report, not as performance."
        )
    if agg_prev["baseline_slot"] != agg_curr["baseline_slot"]:
        warning_codes.append({"code": "slot_differs", "a": agg_prev["baseline_slot"],
                              "b": agg_curr["baseline_slot"]})
        warnings.append(
            f"The prevailing baseline slot differs between snapshots "
            f"({agg_prev['baseline_slot']} then {agg_curr['baseline_slot']}). The two "
            "aggregate figures are not comparable until one slot is chosen for both."
        )
    if inserted or removed:
        warning_codes.append({"code": "scope", "i": len(inserted), "r": len(removed)})
        warnings.append(
            f"{len(inserted)} activities inserted and {len(removed)} removed. Scope "
            "changed, so the aggregate movement is not purely progress."
        )
    if agg_curr["leaves_with_baseline_cost"] == 0:
        warning_codes.append({"code": "no_weight"})
        warnings.append("No leaf carries baseline cost, so there is no weight to decompose.")

    # ---- what changed in the model itself. Each half that describes ONE snapshot
    # comes from a function called twice, for the reason given at the top.
    bp, bc = Basis(prev), Basis(curr)
    matched_prev = {p["uid"] for p, _, _ in pairs}
    matched_curr = {c["uid"] for _, c, _ in pairs}
    inserted_all = [t for t in curr["tasks"] if t["uid"] not in matched_curr]
    removed_all = [t for t in prev["tasks"] if t["uid"] not in matched_prev]
    fin_prev, fin_curr = project_finish(prev), project_finish(curr)
    to_curr = {p["uid"]: c["uid"] for p, c, _ in pairs}
    prev_driver_now = to_curr.get((fin_prev["driver"] or {}).get("uid"))
    finish_block = {
        "previous": fin_prev, "current": fin_curr,
        "delta_days": days_between(fin_prev["finish"], fin_curr["finish"]),
        "delta_unit": "calendar days",
        "driver_changed": (None if not (fin_prev["driver"] and fin_curr["driver"])
                           else prev_driver_now != fin_curr["driver"]["uid"]),
    }
    critical = critical_path_changes(pairs, [t for t in inserted_all if leaf(t)],
                                     prev, curr, bp, bc)
    logic = logic_changes(pairs, inserted_all, removed_all, prev, curr, bp, bc)
    durations = duration_changes(pairs, bp, bc)
    past = past_rewritten(pairs)
    quality = quality_side_by_side(prev, curr)
    if past["activities"]:
        warning_codes.append({"code": "past_rewritten", "n": past["activities"]})
        warnings.append(
            f"The past was rewritten on {past['activities']} activities: an actual date "
            "changed or disappeared, or a percent complete went down, between these two "
            "snapshots. Whatever the previous cycle reported on those activities rested "
            "on a record that no longer exists. Ask for the correction to be stated."
        )

    result = {
        "previous": {"source": os.path.basename(prev.get("source") or ""),
                     "title": prev["project"].get("title") or prev["project"].get("name"),
                     **agg_prev},
        "current": {"source": os.path.basename(curr.get("source") or ""),
                    "title": curr["project"].get("title") or curr["project"].get("name"),
                    **agg_curr},
        "movement_points": (
            zero(agg_curr["percent_earned"] - agg_prev["percent_earned"])
            if agg_curr["percent_earned"] is not None and agg_prev["percent_earned"] is not None
            else None
        ),
        "decomposition_sums_to_points": zero(total),
        # The gap between the headline movement and the sum of the per-activity
        # contributions. It is NOT rounding: it is everything that moved the
        # aggregate without being progress -- scope inserted or removed changing
        # the denominator, a rebased baseline, a slot change. Naming it is the
        # point. An unnamed residue is where a plausible wrong number lives.
        "movement_unexplained_points": None,
        "conventions": {
            "matching": "stable UID, then name plus WBS path; two classes only",
            "population": "leaf, active, non-external, non-milestone",
            "denominator": "current snapshot budget at completion",
            "aggregates": "both snapshots computed by one function called twice",
            "logic_population": "leaf, active, non-external; milestones included",
            "critical": "the tool's Critical flag when the file carries it, otherwise "
                        "total float at or below zero; finished activities are on no path",
            "links": "a link is its two ends, each matched like the activities; links "
                     "touching inserted or removed activities are counted as scope",
            "finish_delta": "calendar days between the two project finish dates",
            "float_and_duration": "working days of each activity's own calendar",
        },
        "warnings": warnings,
        "warning_codes": warning_codes,
        "project_finish": finish_block,
        "critical_path": critical,
        "logic": logic,
        "duration_changed": durations,
        "past_rewritten": past,
        "quality": quality,
        "trend": trend,
        "baseline_moved": baseline_moved,
        "unmatched": {
            "inserted": [{"uid": t["uid"], "id": t["id"], "name": t["name"]} for t in inserted],
            "removed": [{"uid": t["uid"], "id": t["id"], "name": t["name"]} for t in removed],
        },
        "decomposition": decomposition,
    }
    if result["movement_points"] is not None:
        gap = zero(result["movement_points"] - total)
        result["movement_unexplained_points"] = gap
        if abs(gap) >= 0.01:
            result["warning_codes"].append({"code": "residue", "gap": gap})
            result["warnings"].append(
                f"{gap:+.4f} percentage points of the movement are NOT explained by "
                "per-activity progress. Something other than work done moved the "
                "aggregate: scope changing the denominator, a rebased baseline, or a "
                "different baseline slot. Do not report the headline movement as "
                "progress until this residue is accounted for."
            )
    return result


def report(r: dict) -> str:
    L = ["Cycle comparison", ""]
    L.append(f"  previous  {r['previous']['source']}  status {r['previous']['status_date']}")
    L.append(f"  current   {r['current']['source']}  status {r['current']['status_date']}")
    L.append("")
    L.append(f"  earned    {r['previous']['percent_earned']}%  ->  {r['current']['percent_earned']}%")
    L.append(f"  movement  {r['movement_points']} percentage points")
    L.append(f"  decomposition sums to {r['decomposition_sums_to_points']} points")
    L.append(f"  unexplained residue  {r['movement_unexplained_points']} points")
    L.append("")
    exec_n = sum(1 for t in r["trend"] if t["reading"] == "execution")
    replan_n = sum(1 for t in r["trend"] if t["reading"] == "replan")
    L += [
        "  dates moved:",
        f"    {exec_n} with actuals behind them        -> execution",
        f"    {replan_n} with no actuals                -> replan",
        f"    {len(r['baseline_moved'])} with the BASELINE itself moved  -> the reference moved",
        "",
        f"  scope: {len(r['unmatched']['inserted'])} inserted, {len(r['unmatched']['removed'])} removed",
        "",
    ]
    pf, cp, lg, pr = r["project_finish"], r["critical_path"], r["logic"], r["past_rewritten"]
    L += [
        f"  project finish: {pf['previous']['finish']} -> {pf['current']['finish']}"
        f"  ({pf['delta_days']} {pf['delta_unit']})",
        f"  critical path: {len(cp['entered'])} entered, {len(cp['left'])} left, "
        f"{cp['float_fell_count']} lost a day of float or more",
        f"  logic: {len(lg['links_added'])} links added, {len(lg['links_removed'])} removed, "
        f"{len(lg['lag_changed'])} lags and {len(lg['type_changed'])} types changed; "
        f"constraints {len(lg['constraints_added'])} added, "
        f"{len(lg['constraints_changed'])} changed, {len(lg['constraints_removed'])} removed",
        f"  duration changed on work not started: {len(r['duration_changed'])}",
        f"  PAST REWRITTEN: {len(pr['actual_start'])} actual starts, "
        f"{len(pr['actual_finish'])} actual finishes, "
        f"{len(pr['percent_decreased'])} percents that went down",
        "",
    ]
    if r["warnings"]:
        L.append("  WARNINGS:")
        L += [f"    * {w}" for w in r["warnings"]]
        L.append("")
    if r["decomposition"]:
        L.append("  largest contributions to the movement:")
        for d in r["decomposition"][:10]:
            L.append(
                f"    {d['contribution_points']:+8.4f} pp  id {d['id']:<5} "
                f"{d['percent_previous']:>5.1f}% -> {d['percent_current']:>5.1f}%  {d['name']}"
            )
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("previous", help="JSON model of the earlier snapshot")
    ap.add_argument("current", help="JSON model of the later snapshot")
    ap.add_argument("--json", help="write the full comparison here")
    args = ap.parse_args()

    with open(args.previous, encoding="utf-8") as fh:
        prev = json.load(fh)
    with open(args.current, encoding="utf-8") as fh:
        curr = json.load(fh)
    res = compare(prev, curr)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, ensure_ascii=False)
        print(f"comparison -> {args.json}", file=sys.stderr)
    print(report(res))


if __name__ == "__main__":
    main()
