#!/usr/bin/env python3
"""Does this schedule hold up as a model, before any date is discussed?

    python3 network_quality.py model.json [schedule.xml] -o quality.json

The mechanical metrics of the DCMA 14-point schedule assessment, each with its
formula and its published threshold, plus the qualitative parameters a planner
asks of any schedule. **This is an implementation of the metrics, not a
certification against the standard**: the thresholds are quoted so they can be
argued with, the counting conventions are declared, and two of the fourteen (the
critical path test, and the length index when no deadline exists) are reported as
not computable from a file rather than approximated.

Population for every metric: leaf, active, non-external activities; milestones
included unless stated. Working days are counted on each activity's own calendar.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import calendars as cal_mod

NS = "{http://schemas.microsoft.com/project}"
HIGH_FLOAT_DAYS = 44
HIGH_DURATION_DAYS = 44
HARD_CONSTRAINTS = {2: "MSO", 3: "MFO", 5: "SNLT", 7: "FNLT"}
SOFT_CONSTRAINTS = {4: "SNET", 6: "FNET", 1: "ALAP"}

# code, threshold (share of population, in percent; None = count only), direction
METRICS = [
    ("Q1", 5.0), ("Q2", 0.0), ("Q3", 5.0), ("Q4", 10.0), ("Q5", 5.0), ("Q6", 5.0),
    ("Q7", 0.0), ("Q8", 5.0), ("Q9", 0.0), ("Q10", None), ("Q11", 5.0),
    ("Q12", None), ("Q13", None), ("Q14", None),
]


def dt(v):
    return datetime.fromisoformat(v) if v else None


def considered(t):
    return not t.get("summary") and t.get("active") is not False and not t.get("external")


def row(t, extra=None):
    d = {"id": t["id"], "uid": t["uid"], "name": t["name"]}
    if extra:
        d.update(extra)
    return d


def assigned_tasks(xml_path: str | None) -> set:
    """Task UIDs that carry at least one real assignment. Streamed, XML only."""
    out = set()
    if not xml_path:
        return out
    known = set()
    for ev, el in ET.iterparse(xml_path, events=("end",)):
        if el.tag == NS + "Resource":
            uid = el.findtext(NS + "UID")
            if uid:
                known.add(uid)
            el.clear()
        elif el.tag == NS + "Assignment":
            # "No resource" is written two ways: resource -1, or a resource UID
            # that exists in no Resource element. Both mean nothing to trend.
            ruid = el.findtext(NS + "ResourceUID")
            if ruid and ruid != "-1" and ruid in known:
                tu = el.findtext(NS + "TaskUID")
                if tu:
                    out.add(int(tu))
            el.clear()
        elif el.tag in (NS + "Task", NS + "Calendar"):
            el.clear()
    return out


def build(model: dict, xml_path: str | None = None) -> dict:
    tasks = [t for t in model["tasks"] if considered(t)]
    by_uid = {t["uid"]: t for t in model["tasks"]}
    status = dt(model["project"].get("status_date"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    project_finish = dt(model["project"].get("finish"))

    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal = cal_blob.get("default_uid")

    def day_minutes(t):
        c = cal_mod.resolve(cals, t.get("calendar_uid"), default_cal)
        return c.day_minutes if c else ((model.get("units") or {}).get("minutes_per_day") or 480)

    incomplete = [t for t in tasks if not t.get("actual_finish")]
    incomplete_non_ms = [t for t in incomplete if not t.get("milestone")]
    links = [(t, l) for t in tasks for l in (t.get("predecessors") or [])
             if l.get("predecessor_uid") in by_uid]
    has_succ = set(l["predecessor_uid"] for _, l in links)

    findings = {}

    # Q1 -- missing logic: incomplete activities with no predecessor or no successor.
    q1 = []
    for t in incomplete_non_ms:
        no_pred = not t.get("predecessors")
        no_succ = t["uid"] not in has_succ
        if no_pred or no_succ:
            q1.append(row(t, {"missing": "both" if no_pred and no_succ else
                              ("predecessor" if no_pred else "successor"),
                              "finish": t.get("finish")}))
    findings["Q1"] = (q1, len(incomplete_non_ms))

    # Q2 -- leads (negative lag); Q3 -- lags (positive); Q4 -- relationship types.
    q2, q3, q4 = [], [], []
    for t, l in links:
        lag = l.get("lag_minutes") or 0.0
        mpd = day_minutes(t)
        pred = by_uid[l["predecessor_uid"]]
        base = {"predecessor_id": pred["id"], "predecessor_name": pred["name"],
                "link_type": l["type"], "lag_days": round(lag / mpd, 2)}
        if lag < 0:
            q2.append(row(t, base))
        elif lag > 0:
            q3.append(row(t, base))
        if l["type"] != "FS":
            q4.append(row(t, base))
    findings["Q2"] = (q2, len(links))
    findings["Q3"] = (q3, len(links))
    findings["Q4"] = (q4, len(links))

    # Q5 -- hard constraints on incomplete activities; soft ones counted alongside.
    q5, soft = [], []
    for t in incomplete:
        ct = t.get("constraint_type")
        if ct in HARD_CONSTRAINTS:
            q5.append(row(t, {"constraint": HARD_CONSTRAINTS[ct]}))
        elif ct in SOFT_CONSTRAINTS:
            soft.append(row(t, {"constraint": SOFT_CONSTRAINTS[ct]}))
    findings["Q5"] = (q5, len(incomplete))

    # Q6 -- high float; Q7 -- negative float.
    q6, q7 = [], []
    for t in incomplete:
        sl = t.get("total_slack_minutes")
        if sl is None:
            continue
        days = sl / day_minutes(t)
        if days > HIGH_FLOAT_DAYS:
            q6.append(row(t, {"float_days": round(days, 1)}))
        elif days < 0:
            q7.append(row(t, {"float_days": round(days, 1)}))
    findings["Q6"] = (q6, len(incomplete))
    findings["Q7"] = (q7, len(incomplete))

    # Q8 -- high duration: remaining duration over the threshold, incomplete, not milestones.
    q8 = []
    for t in incomplete_non_ms:
        rem = t.get("remaining_duration_minutes")
        if rem is None:
            rem = t.get("duration_minutes")
        if rem is not None and rem / day_minutes(t) > HIGH_DURATION_DAYS:
            q8.append(row(t, {"remaining_days": round(rem / day_minutes(t), 1)}))
    findings["Q8"] = (q8, len(incomplete_non_ms))

    # Q9 -- invalid dates: actuals after the status date. Forecast dates before the
    # status date without actuals are the H finding of the critical review, and are
    # referenced rather than counted twice.
    q9 = []
    if status:
        for t in tasks:
            for k in ("actual_start", "actual_finish"):
                d = dt(t.get(k))
                if d and d > status:
                    q9.append(row(t, {"field": k, "date": t[k]}))
    findings["Q9"] = (q9, len(tasks))

    # Q10 -- activities with duration and no assignment at all.
    assigned = assigned_tasks(xml_path)
    q10 = []
    if assigned:
        for t in incomplete_non_ms:
            if (t.get("duration_minutes") or 0) > 0 and t["uid"] not in assigned:
                q10.append(row(t, {"finish": t.get("finish")}))
    findings["Q10"] = (q10, len(incomplete_non_ms) if assigned else 0)

    # Q11 -- missed activities: baseline finish on or before the status date, and not
    # finished by then (or finished later).
    q11, due = [], 0
    if status and slot:
        for t in tasks:
            bf = dt(((t.get("baselines") or {}).get(slot) or {}).get("finish"))
            if bf is None or bf > status:
                continue
            due += 1
            af = dt(t.get("actual_finish"))
            if af is None or af > bf:
                q11.append(row(t, {"baseline_finish": bf.isoformat(),
                                   "actual_finish": t.get("actual_finish")}))
    findings["Q11"] = (q11, due)

    # Q12 -- critical path test: needs the schedule to be perturbed. Not from a file.
    findings["Q12"] = ([], 0)

    # Q13 -- critical path length index. Needs a deadline on the finish milestone to
    # give the path a float; without one the index is 1.0 by construction and says
    # nothing. Reported as such.
    critical = [t for t in incomplete if t.get("critical")]
    finish_ms = [t for t in tasks if t.get("milestone") and t.get("finish")]
    finish_ms.sort(key=lambda t: t["finish"], reverse=True)
    last_ms = finish_ms[0] if finish_ms else None
    cpli = None
    cpl_days = None
    if status and project_finish and project_finish > status:
        cpl_days = (project_finish - status).days
        tf = (last_ms.get("total_slack_minutes") or 0) / day_minutes(last_ms) if last_ms else 0.0
        cpli = round((cpl_days + tf) / cpl_days, 3) if cpl_days else None
    findings["Q13"] = ([], 0)

    # Q14 -- baseline execution index: finished on time / due by the status date.
    bei = None
    if due:
        on_time = due - len(q11)
        bei = round(on_time / due, 3)
    findings["Q14"] = ([], due)

    # Qualitative extras a planner asks for, beyond the fourteen.
    summaries_with_links = [row(t) for t in model["tasks"]
                            if t.get("summary") and (t.get("predecessors") or t["uid"] in has_succ)]
    milestones_no_deadline = [row(t) for t in tasks if t.get("milestone") and not t.get("deadline")]
    critical_reaches_end = bool(last_ms and last_ms.get("critical"))

    metrics = []
    for code, threshold in METRICS:
        items, pop = findings[code]
        share = round(len(items) / pop * 100, 2) if pop else None
        status_word = None
        if threshold is not None and share is not None:
            status_word = "pass" if share <= threshold else "fail"
        entry = {
            "code": code, "count": len(items), "population": pop, "share_pct": share,
            "threshold_pct": threshold, "status": status_word, "direction": "max",
            "items": items[:400],
        }
        if code == "Q14" and due:
            # The index itself, with its floor: finished on time over due.
            entry.update({"count": due - len(q11), "share_pct": round(bei * 100, 2),
                          "threshold_pct": 95.0, "direction": "min",
                          "status": "pass" if bei >= 0.95 else "fail"})
        metrics.append(entry)

    return {
        "status_date": model["project"].get("status_date"),
        "population": {"leaves": len(tasks), "incomplete": len(incomplete),
                       "links": len(links), "critical_incomplete": len(critical)},
        "metrics": metrics,
        "soft_constraints": {"count": len(soft), "items": soft[:200]},
        "indices": {
            "bei": bei, "bei_due": due, "bei_on_time": (due - len(q11)) if due else None,
            "cpli": cpli, "cpl_days": cpl_days,
            "cpli_meaningful": bool(last_ms and last_ms.get("deadline")),
            "critical_activities": len(critical),
            "critical_reaches_final_milestone": critical_reaches_end,
            "final_milestone_id": last_ms["id"] if last_ms else None,
            "final_milestone_finish": last_ms.get("finish") if last_ms else None,
        },
        "qualitative": {
            "summaries_with_links": summaries_with_links[:200],
            "summaries_with_links_count": len(summaries_with_links),
            "milestones_without_deadline": len(milestones_no_deadline),
            "milestones": len([t for t in tasks if t.get("milestone")]),
        },
        "provenance": "implementation of the DCMA 14-point metrics with quoted thresholds; "
                      "not a certification. Q12 needs the schedule perturbed and Q13 needs a "
                      "deadline on the finish milestone; both reported as not computable when so.",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model")
    ap.add_argument("xml", nargs="?")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    res = build(model, args.xml)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    for m in res["metrics"]:
        print(f"  {m['code']:<4} {m['count']:>6} / {m['population']:<6} {str(m['share_pct']):>7}%  "
              f"{'' if m['threshold_pct'] is None else '<= ' + str(m['threshold_pct']) + '%':<9} {m['status'] or ''}",
              file=sys.stderr)
    print(f"  BEI {res['indices']['bei']}  CPLI {res['indices']['cpli']} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
