#!/usr/bin/env python3
"""Productivity and trend per resource, from the file's own assignment data.

    python3 resources.py schedule.xml model.json -o productivity.json

Nothing here reads a custom field. For a material resource Project stores the
quantity in the work fields, as hours in the ISO duration: `PT10567H` is 10,567
units of whatever the resource's material label says. Measured on a 6,484-task
export against a hand-kept quantity column: identical. The same rule gives the
executed quantity (actual work), the remaining quantity, the baseline quantity,
and the executed quantity per day (time-phased actual work, block type 2).

Three rates per activity, because one is not a fair reading:

* **own** -- what this activity has practised since it started, on its calendar;
* **global** -- everything executed for that resource across every front, over
  the working time it took; the fair scenario, which dilutes a rainy fortnight;
* **recent** -- the resource's last thirty days, because the rate of three months
  ago is not the rate of today.

Four dates and three verdicts per activity, in order of gravity:

* projected after the trend finish but not after the baseline finish: **reprogram**;
* after the baseline finish but not after the late finish: **baseline delay**, the
  float absorbs it and the report says how much float is left;
* after the late finish: **critical**, and the report says on which date.

Where the executed quantity was not entered but the physical percent was, the
executed quantity is percent times planned and the row says `inferred`. Validate
the fill before trending, or the trend inherits the hole.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta

import calendars as cal_mod
from parse_mspdi import iso_duration_minutes

NS = "{http://schemas.microsoft.com/project}"
TYPE_ACTUAL_WORK = "2"
TYPE_BASELINE_WORK = "4"
RECENT_DAYS = 30
UNASSIGNED = "-1"


def dt(v):
    return datetime.fromisoformat(v) if v else None


def _num(v):
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else None
    except ValueError:
        return None


def qty(iso):
    """Material quantity encoded as hours of an ISO duration."""
    m = iso_duration_minutes(iso)
    return None if m is None else m / 60.0


def stream(path: str):
    """One pass over the file: resources first, then assignments."""
    resources = {}
    for ev, el in ET.iterparse(path, events=("end",)):
        tag = el.tag.replace(NS, "")
        if tag == "Resource":
            uid = el.findtext(NS + "UID")
            if uid:
                resources[uid] = {
                    "uid": uid, "name": el.findtext(NS + "Name"),
                    "type": {"0": "material", "1": "work", "2": "cost"}.get(
                        el.findtext(NS + "Type"), "unknown"),
                    "label": el.findtext(NS + "MaterialLabel"),
                }
            el.clear()
        elif tag == "Assignment":
            ruid = el.findtext(NS + "ResourceUID")
            tuid = el.findtext(NS + "TaskUID")
            bl = el.find(NS + "Baseline")
            rec = {
                "resource_uid": ruid, "task_uid": int(tuid) if tuid else None,
                "planned": qty(bl.findtext(NS + "Work")) if bl is not None else None,
                "executed": qty(el.findtext(NS + "ActualWork")),
                "remaining": qty(el.findtext(NS + "RemainingWork")),
                "actual_start": el.findtext(NS + "ActualStart"),
                "actual_finish": el.findtext(NS + "ActualFinish"),
                "actual_by_day": defaultdict(float),
            }
            for tp in el.findall(NS + "TimephasedData"):
                if tp.findtext(NS + "Type") != TYPE_ACTUAL_WORK:
                    continue
                v = qty(tp.findtext(NS + "Value"))
                day = (tp.findtext(NS + "Start") or "")[:10]
                if v and day and day >= "1990-01-01":
                    rec["actual_by_day"][day] += v
            el.clear()
            yield resources, rec


def working_days_between(cal, a, b):
    if a is None or b is None:
        return None
    if cal is None:
        return max(1, (b.date() - a.date()).days + 1)
    return max(1, abs(cal.working_days(a, b) or 0))


def add_working_days(cal, start: datetime, days: float, limit_days: int = 3660):
    """The date `days` working days after `start`, on the calendar."""
    if days <= 0:
        return start
    remaining = days
    cur = start.date()
    steps = 0
    while remaining > 0 and steps < limit_days:
        cur += timedelta(days=1)
        steps += 1
        if cal is None or cal.is_working(cur):
            remaining -= 1
    return datetime(cur.year, cur.month, cur.day, 17, 0)


def verdict(projected, trend, baseline, late):
    if projected is None:
        return None
    if trend and projected <= trend:
        return "ahead"
    if baseline and projected <= baseline:
        return "reprogram"
    if late and projected <= late:
        return "baseline_delay"
    return "critical"


def build(xml_path: str, model: dict, profile: dict | None = None) -> dict:
    prof = (profile or {}).get("productivity") or {}
    recent_days = int(prof.get("recent_days") or RECENT_DAYS)
    thin_days = float(prof.get("thin_evidence_days") or 10)
    thin_share = float(prof.get("thin_evidence_share") or 0.02)
    contracted_ref = ((profile or {}).get("fields") or {}).get("productivity_contracted")
    contracted_field = None
    if contracted_ref:
        import profile as prof_mod
        row = prof_mod.resolve_field(model, contracted_ref)
        contracted_field = row["field_id"] if row else None
    status = dt(model["project"].get("status_date"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    tasks = {t["uid"]: t for t in model["tasks"]}
    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal = cal_blob.get("default_uid")
    if cals:
        stamps = [dt(v) for t in model["tasks"] for v in (t.get("start"), t.get("finish")) if v]
        if stamps:
            cal_mod.prepare(cals, min(stamps).date(), max(stamps).date())

    def cal_for(t):
        return cal_mod.resolve(cals, t.get("calendar_uid"), default_cal)

    resources = {}
    per_resource = defaultdict(lambda: {"assignments": 0, "planned": 0.0, "executed": 0.0,
                                        "remaining": 0.0, "executed_days": 0.0,
                                        "recent_qty": 0.0, "recent_days": 0.0,
                                        "planned_days": 0.0})
    rows = []
    unassigned = 0
    recent_from = (status - timedelta(days=recent_days)).date().isoformat() if status else None
    cutoff = status.date().isoformat() if status else "9999-12-31"

    for res, a in stream(xml_path):
        resources = res
        if a["resource_uid"] in (None, UNASSIGNED) or a["resource_uid"] not in res:
            unassigned += 1
            continue
        r = res[a["resource_uid"]]
        if r["type"] == "cost":
            continue
        t = tasks.get(a["task_uid"])
        if t is None or t.get("summary") or t.get("active") is False:
            continue
        cal = cal_for(t)
        planned = a["planned"] or 0.0
        executed = a["executed"] or 0.0
        executed_source = "actual"
        phys = t.get("physical_percent_complete")
        if executed <= 0 and planned > 0 and phys:
            executed = planned * phys / 100.0
            executed_source = "inferred"
        remaining = a["remaining"] if a["remaining"] is not None else max(0.0, planned - executed)
        a_start = dt(a["actual_start"] or t.get("actual_start"))
        a_finish = dt(a["actual_finish"] or t.get("actual_finish"))

        pr = per_resource[r["uid"]]
        pr["assignments"] += 1
        pr["planned"] += planned
        pr["executed"] += executed if executed_source == "actual" else 0.0
        pr["remaining"] += remaining
        bl = (t.get("baselines") or {}).get(slot) or {}
        bdays = working_days_between(cal, dt(bl.get("start")), dt(bl.get("finish")))
        if planned > 0 and bdays:
            pr["planned_days"] += bdays

        own_rate = None
        exec_days = None
        if a_start and executed > 0 and status:
            end = a_finish if a_finish and a_finish <= status else status
            exec_days = working_days_between(cal, a_start, end)
            own_rate = executed / exec_days if exec_days else None
            if executed_source == "actual":
                pr["executed_days"] += exec_days
        for day, v in a["actual_by_day"].items():
            if recent_from and recent_from <= day <= cutoff:
                pr["recent_qty"] += v
        if recent_from and a_start and executed_source == "actual":
            win_start = max(a_start, dt(recent_from + "T00:00:00"))
            win_end = a_finish if a_finish and a_finish <= status else status
            if win_end and win_end >= win_start:
                pr["recent_days"] += working_days_between(cal, win_start, win_end)

        rows.append({
            "id": t["id"], "uid": t["uid"], "name": t["name"],
            "resource_uid": r["uid"], "resource": r["name"], "unit": r["label"] or r["type"],
            "planned_qty": round(planned, 2), "executed_qty": round(executed, 2),
            "executed_source": executed_source, "remaining_qty": round(remaining, 2),
            "rate_own": round(own_rate, 3) if own_rate else None,
            "rate_planned": round(planned / bdays, 3) if (planned > 0 and bdays) else None,
            "_cal": cal, "_trend": dt(t.get("finish")), "_baseline": dt(bl.get("finish")),
            "_late": dt(t.get("late_finish")), "_started": bool(a_start),
            "_finished": bool(a_finish),
            "float_days": (round(t["total_slack_minutes"] / (cal.day_minutes if cal else 480), 1)
                           if t.get("total_slack_minutes") is not None else None),
            "critical_now": bool(t.get("critical")),
            # The organisation's contracted rate, when its profile names the field.
            # An overlay for comparison, never a requirement.
            "rate_contracted": (_num((t.get("custom") or {}).get(contracted_field))
                                if contracted_field else None),
        })

    # ---- resource-level rates
    res_out = []
    for uid, pr in per_resource.items():
        r = resources[uid]
        pr_rate = pr["executed"] / pr["executed_days"] if pr["executed_days"] else None
        rc_rate = pr["recent_qty"] / pr["recent_days"] if pr["recent_days"] else None
        pl_rate = pr["planned"] / pr["planned_days"] if pr["planned_days"] else None
        # A rate built on a handful of days, or on a sliver of the planned quantity,
        # projects nonsense with a straight face: a resource with 2% executed over
        # three days "finishes" in 2031. The rate is still reported -- it is what the
        # data says -- but flagged, and the verdict it drives is flagged with it.
        thin = (pr["executed_days"] < thin_days) or (pr["planned"] > 0 and pr["executed"] < thin_share * pr["planned"])
        res_out.append({
            "uid": uid, "name": r["name"], "type": r["type"], "unit": r["label"] or r["type"],
            "assignments": pr["assignments"],
            "executed_days": round(pr["executed_days"], 1),
            "thin_evidence": bool(thin),
            "planned_qty": round(pr["planned"], 2), "executed_qty": round(pr["executed"], 2),
            "remaining_qty": round(pr["remaining"], 2),
            "rate_global": round(pr_rate, 3) if pr_rate else None,
            "rate_recent": round(rc_rate, 3) if rc_rate else None,
            "rate_planned": round(pl_rate, 3) if pl_rate else None,
            "progress_pct": round(pr["executed"] / pr["planned"] * 100, 2) if pr["planned"] else None,
        })
    res_out.sort(key=lambda r: r["planned_qty"], reverse=True)
    res_by = {r["uid"]: r for r in res_out}

    # ---- projections, only for activities in progress with something left
    fmt = lambda d: d.strftime("%Y-%m-%d") if d else None
    activities = []
    counts = defaultdict(int)
    for row in rows:
        if not row["_started"] or row["_finished"] or row["remaining_qty"] <= 0:
            continue
        r = res_by.get(row["resource_uid"], {})
        cal = row["_cal"]
        rates = {"own": row["rate_own"], "global": r.get("rate_global"),
                 "recent": r.get("rate_recent")}
        projected = {}
        for k, rate in rates.items():
            if rate and status:
                projected[k] = add_working_days(cal, status, row["remaining_qty"] / rate)
            else:
                projected[k] = None
        verdicts = {k: verdict(p, row["_trend"], row["_baseline"], row["_late"])
                    for k, p in projected.items()}
        req_trend = req_late = None
        if status and row["_trend"] and row["_trend"] > status:
            req_trend = row["remaining_qty"] / working_days_between(cal, status, row["_trend"])
        if status and row["_late"] and row["_late"] > status:
            req_late = row["remaining_qty"] / working_days_between(cal, status, row["_late"])
        days_to_critical = None
        if projected.get("global") and row["_late"]:
            days_to_critical = (row["_late"] - projected["global"]).days
        counts[verdicts.get("global") or "none"] += 1
        activities.append({
            **{k: v for k, v in row.items() if not k.startswith("_")},
            "rate_global": r.get("rate_global"), "rate_recent": r.get("rate_recent"),
            "rate_required_trend": round(req_trend, 3) if req_trend else None,
            "rate_required_late": round(req_late, 3) if req_late else None,
            "finish_trend": fmt(row["_trend"]), "finish_baseline": fmt(row["_baseline"]),
            "finish_late": fmt(row["_late"]),
            "projected_own": fmt(projected["own"]), "projected_global": fmt(projected["global"]),
            "projected_recent": fmt(projected["recent"]),
            "verdict_own": verdicts["own"], "verdict_global": verdicts["global"],
            "verdict_recent": verdicts["recent"],
            "days_of_float_left_global": days_to_critical,
            "thin_evidence": bool(r.get("thin_evidence")) or row["executed_source"] == "inferred",
        })
    order = {"critical": 0, "baseline_delay": 1, "reprogram": 2, "ahead": 3, None: 4}
    activities.sort(key=lambda a: (order.get(a["verdict_global"], 4), -(a["planned_qty"] or 0)))

    return {
        "status_date": model["project"].get("status_date"),
        "recent_window_days": recent_days,
        "summary": {
            "resources_tracked": len(res_out),
            "assignments_unassigned": unassigned,
            "activities_projected": len(activities),
            "verdicts": dict(counts),
            "inferred_executed": sum(1 for a in activities if a["executed_source"] == "inferred"),
            "thin_evidence": sum(1 for a in activities if a["thin_evidence"]),
        },
        "provenance": {
            "quantities": "measured: assignment work fields, material quantity as hours of the "
                          "ISO duration; executed = actual work, remaining = remaining work",
            "rates": "measured where executed quantity was entered; inferred where it was "
                     "derived from physical percent, and flagged per row",
            "projection": "remaining quantity over each rate, in working days of the "
                          "activity's own calendar, from the status date",
            "verdict": "against trend finish, baseline finish and the file's late finish",
        },
        "resources": res_out,
        "activities": activities,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("xml")
    ap.add_argument("model", help="JSON produced by parse_mspdi.py")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    res = build(args.xml, model)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    s = res["summary"]
    print(f"{s['resources_tracked']} resources, {s['activities_projected']} activities projected, "
          f"verdicts {s['verdicts']} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
