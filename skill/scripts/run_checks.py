#!/usr/bin/env python3
"""Run the schedule integrity checks over a parsed MSPDI model.

    python3 parse_mspdi.py delivery.xml -o model.json
    python3 run_checks.py model.json                    # human summary
    python3 run_checks.py model.json --json findings.json

Design rules this file obeys, all of them from the method:

* Network checks run first, and their result gates the rest. When the tool
  recalculates over a violated network, every forecast date in the file is
  computed from logic the works does not follow.
* Every finding carries the visible row number next to the stable UID, because
  the visible one is the only identifier a person can see on their screen.
* Every threshold declares its unit and its counting convention. "How many
  activities have the problem" depends on how you count, and diverging from the
  convention of the tool the other party uses hands them the argument.
* A predecessor that is 100% physically complete with no actual finish is a
  reporting defect (P), not a network breach. It migrates out of A1/A2.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta

import calendars as cal_mod

DEFAULT_THRESHOLD_DAYS = 30
DEFAULT_TOLERANCE_DAYS = 1


def dt(value):
    return datetime.fromisoformat(value) if value else None


def calendar_days(a, b):
    """Signed calendar-day difference b - a."""
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 86400.0


def working_days(a, b, calendar=None):
    """Signed working-day count between two dates, by the task's own calendar.

    The calendar is not decoration. A real programme was measured with 107 of them:
    the default worked 8 hours over 5 days, while the calendars carrying 90% of the
    tasks worked 9 hours over 6 days, and a rainy-season calendar held 616
    non-working days of weather reserve. Counting Monday to Friday and dividing by
    the header's minutes-per-day flagged 27% of that schedule as inconsistent, with
    a median disagreement of two days -- pure noise, burying the 64 activities that
    genuinely disagreed by more than sixty days.

    A calendar is passed in every real path. The weekday fallback exists only for
    a file that ships no calendars at all, and it is declared in the output so
    nobody mistakes it for a measurement.
    """
    if a is None or b is None:
        return None
    if calendar is not None:
        return calendar.working_days(a, b)
    sign = 1 if b >= a else -1
    lo, hi = sorted((a.date(), b.date()))
    days = 0
    cur = lo
    while cur <= hi:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return sign * days


def finish_variance_days(task, slot, calendar=None):
    """Finish minus baseline finish, in calendar days and in working days."""
    bl = (task.get("baselines") or {}).get(slot) if slot else None
    bf = dt(bl.get("finish")) if bl else None
    f = dt(task.get("finish"))
    if bf is None or f is None:
        return None, None
    return calendar_days(bf, f), working_days(bf, f, calendar)


def has_actual(task) -> bool:
    return bool(task.get("actual_start") or task.get("actual_finish"))


def pct(task):
    """Physical percent when present, else the ordinary percent complete.

    They are different fields. Earned value needs the physical one; it is often
    absent, and falling back is a stated assumption, not an equivalence.
    """
    p = task.get("physical_percent_complete")
    return p if p is not None else task.get("percent_complete")


def is_pending_record(task) -> bool:
    """P: declared complete, no actual finish. A record defect, not execution."""
    return (pct(task) or 0) >= 100 and not task.get("actual_finish")


def considered(task) -> bool:
    """Leaf, active, not external. Summaries would double-count their children."""
    return (
        not task.get("summary")
        and task.get("active") is not False
        and not task.get("external")
    )


def finding(task, code, detail):
    return {
        "code": code,
        "uid": task["uid"],
        "id": task["id"],
        "name": task["name"],
        "wbs": task.get("wbs"),
        **detail,
    }


def run(model: dict, threshold_days: int, tolerance_days: float) -> dict:
    tasks = model["tasks"]
    by_uid = {t["uid"]: t for t in tasks}
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    status = dt(model["project"].get("status_date"))

    cal_blob = (model.get("calendars") or {})
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal_uid = cal_blob.get("default_uid")
    if cals:
        stamps = [
            dt(v) for t in tasks for v in (t.get("start"), t.get("finish"))
            if v
        ]
        if stamps:
            cal_mod.prepare(cals, min(stamps).date(), max(stamps).date())

    def cal_for(task):
        return cal_mod.resolve(cals, task.get("calendar_uid"), default_cal_uid)

    blocking = []
    if status is None:
        blocking.append(
            "No StatusDate in the file. Every adherence check is measured against it, "
            "and defaulting to today would silently change the answer every day the "
            "review is re-run. Set a status date in the schedule and export again."
        )
    if slot is None:
        blocking.append(
            "No baseline slot carries leaf cost above zero, so there is no planned "
            "half to compare against. Save a baseline before reviewing adherence."
        )

    out = {c: [] for c in ("A1", "A2", "H", "E", "C", "G", "B", "F", "P")}

    # ---- Layer 3 first, internally: P must be known before A1/A2 can be judged.
    for t in tasks:
        if considered(t) and is_pending_record(t):
            out["P"].append(
                finding(t, "P", {
                    "percent": pct(t),
                    "actual_start": t.get("actual_start"),
                    "why": "declared complete with no actual finish",
                })
            )
    pending = {f["uid"] for f in out["P"]}

    # ---- Layer 1: network integrity. Both ends of a violated link are marked.
    net_pairs = {"A1": [], "A2": []}
    for succ in tasks:
        if not considered(succ):
            continue
        for link in succ.get("predecessors") or []:
            pred = by_uid.get(link["predecessor_uid"])
            if pred is None or not considered(pred):
                continue
            # The transversal rule: a predecessor that is only pending a record
            # is not an execution breach. It already sits in P.
            if pred["uid"] in pending:
                continue
            pred_done = bool(pred.get("actual_finish"))
            if succ.get("actual_finish") and not pred.get("actual_start"):
                net_pairs["A2"].append((succ, pred, link))
            elif succ.get("actual_start") and not pred_done:
                net_pairs["A1"].append((succ, pred, link))

    for code, pairs in net_pairs.items():
        seen = set()
        for succ, pred, link in pairs:
            for role, task, other in (("successor", succ, pred), ("predecessor", pred, succ)):
                key = (task["uid"], other["uid"], role)
                if key in seen:
                    continue
                seen.add(key)
                out[code].append(
                    finding(task, code, {
                        "role": role,
                        "link_type": link["type"],
                        "lag_minutes": link.get("lag_minutes"),
                        "counterpart_uid": other["uid"],
                        "counterpart_id": other["id"],
                        "counterpart_name": other["name"],
                    })
                )

    # ---- Layer 2: date adherence.
    for t in tasks:
        if not considered(t):
            continue

        if status is not None:
            f = dt(t.get("finish"))
            if f is not None and f < status and not has_actual(t):
                out["H"].append(
                    finding(t, "H", {
                        "finish": t["finish"],
                        "status_date": model["project"]["status_date"],
                        "days_elapsed": round(calendar_days(f, status), 1),
                    })
                )

        tcal = cal_for(t)
        cal, work = finish_variance_days(t, slot, tcal)
        if cal is not None:
            if cal <= -threshold_days and not t.get("actual_start"):
                out["E"].append(
                    finding(t, "E", {
                        "finish_variance_calendar_days": round(cal, 1),
                        "finish_variance_working_days": work,
                        "baseline_slot": slot,
                        "calendar": tcal.name if tcal else None,
                    })
                )
            elif cal >= threshold_days:
                out["C"].append(
                    finding(t, "C", {
                        "finish_variance_calendar_days": round(cal, 1),
                        "finish_variance_working_days": work,
                        "baseline_slot": slot,
                        "calendar": tcal.name if tcal else None,
                    })
                )

        # ---- Layer 3: reporting consistency.
        s, f = dt(t.get("start")), dt(t.get("finish"))
        dur_min = t.get("duration_minutes")
        # The day length of THIS task's calendar, never the project header's.
        mpd = tcal.day_minutes if tcal else (model.get("units") or {}).get("minutes_per_day")
        if s and f and dur_min is not None and mpd:
            # Working time against working time. Comparing a fractional duration
            # against a count of whole days touched disagrees on every task that
            # starts or ends mid-shift, which is most of them.
            window_min = tcal.working_minutes(s, f) if tcal else None
            if window_min is None:
                span = working_days(s, f, None)
                window_min = (span or 0) * mpd
            if abs(dur_min - window_min) > tolerance_days * mpd:
                out["G"].append(
                    finding(t, "G", {
                        "duration_days": round(dur_min / mpd, 2),
                        "window_working_days": round(window_min / mpd, 2),
                        "gap_days": round((dur_min - window_min) / mpd, 2),
                        "calendar": tcal.name if tcal else None,
                        "note": "thermometer: inspect, do not report alone",
                    })
                )

        if t.get("milestone") and not t.get("deadline"):
            out["B"].append(finding(t, "B", {"finish": t.get("finish")}))

        if t.get("actual_start") and not t.get("actual_finish") and (pct(t) or 0) == 0:
            out["F"].append(
                finding(t, "F", {"actual_start": t["actual_start"], "percent": pct(t)})
            )

    return {
        "source": model.get("source"),
        "blocking": blocking,
        "conventions": {
            "threshold_days": threshold_days,
            "threshold_unit": "calendar days between baseline finish and current finish",
            "tolerance_days": tolerance_days,
            "baseline_slot": slot,
            "baseline_slot_basis": (model.get("prevailing_baseline") or {}).get("basis"),
            "network_counting": (
                "both ends of each violated link are marked, to agree with the "
                "scheduling tool's own routines"
            ),
            "population": "leaf, active, non-external tasks only",
            "working_days": (
                "counted on each task's own calendar, including its exceptions"
                if cals else
                "NO CALENDARS IN FILE: fell back to a Monday-Friday approximation, "
                "which is not a measurement"
            ),
            "calendars_in_file": cal_blob.get("count", 0),
            "calendars_in_use": cal_blob.get("in_use", []),
            "percent_source": "physical percent complete when present, else percent complete",
        },
        "counts": summarise(out),
        "findings": out,
    }


def summarise(out: dict) -> dict:
    """Report all three defensible counts for network findings, not just one."""
    counts = {}
    for code, items in out.items():
        entry = {"marked_rows": len(items), "distinct_activities": len({i["uid"] for i in items})}
        if code in ("A1", "A2"):
            entry["as_successors"] = len({i["uid"] for i in items if i.get("role") == "successor"})
            entry["as_predecessors"] = len(
                {i["uid"] for i in items if i.get("role") == "predecessor"}
            )
        counts[code] = entry
    return counts


LABELS = {
    "A1": "Successor started without the predecessor complete",
    "A2": "Total inversion: successor complete, predecessor not started",
    "H": "Trend date elapsed with no actual progress",
    "E": "Pulled forward beyond threshold and never started",
    "C": "Delayed beyond threshold",
    "G": "Duration disagrees with the start-to-finish window (thermometer)",
    "B": "Milestone with no deadline set",
    "F": "In progress with percent complete at zero",
    "P": "Pending record: declared complete with no actual finish",
}
ORDER = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]


def report(res: dict) -> str:
    lines = [f"Schedule integrity review -- {res['source']}", ""]
    if res["blocking"]:
        lines.append("BLOCKING -- the review cannot be trusted until these are fixed:")
        lines += [f"  * {b}" for b in res["blocking"]] + [""]
    conv = res["conventions"]
    lines += [
        f"Baseline slot used: {conv['baseline_slot']} ({conv['baseline_slot_basis']})",
        f"Threshold: {conv['threshold_days']} {conv['threshold_unit']}",
        f"Population: {conv['population']}",
        f"Counting: {conv['network_counting']}",
        "",
        "Findings, in the order the method runs them:",
        "",
    ]
    for code in ORDER:
        c = res["counts"][code]
        extra = ""
        if code in ("A1", "A2") and c["marked_rows"]:
            extra = (
                f"  [as successors {c['as_successors']}, "
                f"as predecessors {c['as_predecessors']}]"
            )
        lines.append(f"  {code:<3} {c['distinct_activities']:>6} activities  {LABELS[code]}{extra}")
    lines += ["", "Network findings (A1, A2) gate everything below them. If they are non-zero,",
              "every forecast date in this file is computed over logic the works does not follow."]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model", help="JSON produced by parse_mspdi.py")
    ap.add_argument("--threshold-days", type=int, default=DEFAULT_THRESHOLD_DAYS)
    ap.add_argument("--tolerance-days", type=float, default=DEFAULT_TOLERANCE_DAYS)
    ap.add_argument("--json", help="write the full findings here")
    args = ap.parse_args()

    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    res = run(model, args.threshold_days, args.tolerance_days)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, ensure_ascii=False)
        print(f"findings -> {args.json}", file=sys.stderr)
    print(report(res))


if __name__ == "__main__":
    main()
