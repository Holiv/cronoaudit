#!/usr/bin/env python3
"""Run the schedule integrity checks over a parsed MSPDI model.

    python3 parse_mspdi.py delivery.xml -o model.json
    python3 run_checks.py model.json                    # human summary
    python3 run_checks.py model.json --json findings.json

Design rules this file obeys, all of them from the method:

* Network checks run first, and their result gates the rest. When the tool
  recalculates over a violated network, every forecast date in the file is
  computed from logic the works does not follow.
* Every finding carries the visible row number, because it is the only identifier
  a person can see on their screen. The stable UID travels in the data, never in
  the report.
* Every threshold declares its unit and its counting convention. "How many
  activities have the problem" depends on how you count, and diverging from the
  convention of the tool the other party uses hands them the argument.
* A predecessor that is 100% physically complete with no actual finish is a
  reporting defect (P), not a network breach. It migrates out of A1/A2.
* Working time is counted on each activity's own calendar. Never on the header's
  minutes-per-day, never on a five-day week assumption.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta

import calendars as cal_mod

DEFAULT_THRESHOLD_DAYS = 30
DEFAULT_TOLERANCE_DAYS = 1
ORDER = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]


def dt(value):
    return datetime.fromisoformat(value) if value else None


def calendar_days(a, b):
    """Signed calendar-day difference b - a."""
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 86400.0


def working_days(a, b, calendar=None):
    """Signed working-day count between two dates, by the task's own calendar.

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


def signed_working_minutes(a, b, calendar):
    """Working minutes from a to b, negative when b is earlier than a."""
    if a is None or b is None:
        return None
    if calendar is None:
        return (b - a).total_seconds() / 60.0
    minutes = calendar.working_minutes(a, b)
    return minutes if b >= a else -minutes


def has_actual(task) -> bool:
    return bool(task.get("actual_start") or task.get("actual_finish"))


def physical_pct(task):
    """Physical percent when present, else the ordinary percent complete."""
    p = task.get("physical_percent_complete")
    return p if p is not None else task.get("percent_complete")


def is_pending_record(task) -> bool:
    """P: declared physically complete, no actual finish. A record defect."""
    return (physical_pct(task) or 0) >= 100 and not task.get("actual_finish")


def considered(task) -> bool:
    """Leaf, active, not external. Milestones are in; summaries would double-count."""
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


def pair_detail(link, other, role, extra=None):
    d = {
        "role": role,
        "link_type": link["type"],
        "lag_minutes": link.get("lag_minutes"),
        "counterpart_uid": other["uid"],
        "counterpart_id": other["id"],
        "counterpart_name": other["name"],
    }
    if extra:
        d.update(extra)
    return d


def run(model: dict, threshold_days: int, tolerance_days: float) -> dict:
    tasks = model["tasks"]
    by_uid = {t["uid"]: t for t in tasks}
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    status = dt(model["project"].get("status_date"))

    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal_uid = cal_blob.get("default_uid")
    if cals:
        stamps = [dt(v) for t in tasks for v in (t.get("start"), t.get("finish")) if v]
        if stamps:
            cal_mod.prepare(cals, min(stamps).date(), max(stamps).date())

    def cal_for(task):
        return cal_mod.resolve(cals, task.get("calendar_uid"), default_cal_uid)

    def day_minutes(task):
        c = cal_for(task)
        return c.day_minutes if c else ((model.get("units") or {}).get("minutes_per_day") or 480)

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

    out = {c: [] for c in ORDER}
    ignored = {"A1_both_complete": []}
    link_types_seen = {"FS": 0, "SS": 0, "FF": 0, "SF": 0}
    pairs = {"A1": [], "A2": []}

    # ---- P first: a pending record must be known before A1/A2 can be judged.
    for t in tasks:
        if considered(t) and is_pending_record(t):
            out["P"].append(finding(t, "P", {
                "percent": physical_pct(t),
                "actual_start": t.get("actual_start"),
                "why": "pending_record",
            }))
    pending = {f["uid"] for f in out["P"]}

    # ---- Layer 1: network integrity, on actual dates, on the successor's calendar.
    # Every relationship type is evaluated and the lag is honoured, so an
    # intentional overlap (a finish-to-start link with a lead) is not accused.
    for succ in tasks:
        if not considered(succ):
            continue
        scal = cal_for(succ)
        for link in succ.get("predecessors") or []:
            pred = by_uid.get(link["predecessor_uid"])
            if pred is None or not considered(pred):
                continue
            ltype = link["type"]
            link_types_seen[ltype] = link_types_seen.get(ltype, 0) + 1
            lag = link.get("lag_minutes") or 0.0
            if pred["uid"] in pending:
                continue  # a record defect, already in P; not an execution breach

            s_as, s_af = dt(succ.get("actual_start")), dt(succ.get("actual_finish"))
            p_as, p_af = dt(pred.get("actual_start")), dt(pred.get("actual_finish"))

            if ltype == "FS":
                # A2: successor complete, predecessor never started.
                if s_af and not p_as and not p_af:
                    pairs["A2"].append((succ, pred, link, {}))
                    continue
                if not s_as:
                    continue
                if s_af and p_af:
                    # Both complete. Reported only as history: it no longer changes
                    # a forecast, but it is evidence for the forensics.
                    if p_af > s_as:
                        ignored["A1_both_complete"].append({
                            "successor_id": succ["id"], "successor_uid": succ["uid"],
                            "predecessor_id": pred["id"], "predecessor_uid": pred["uid"],
                            "overlap_days": round((p_af - s_as).total_seconds() / 86400.0, 1),
                        })
                    continue
                if not p_af:
                    pairs["A1"].append((succ, pred, link, {"why": "pred_not_finished"}))
                else:
                    gap = signed_working_minutes(p_af, s_as, scal)
                    if gap is not None and gap < lag:
                        pairs["A1"].append((succ, pred, link, {
                            "why": "pred_finished_after_start",
                            "overlap_beyond_lead_days": round((lag - gap) / day_minutes(succ), 2),
                        }))
            elif ltype == "SS":
                if s_as and p_as and not s_af:
                    gap = signed_working_minutes(p_as, s_as, scal)
                    if gap is not None and gap < lag:
                        pairs["A1"].append((succ, pred, link, {
                            "why": "ss_before_lag",
                        }))
                elif s_as and not p_as and not s_af:
                    pairs["A1"].append((succ, pred, link, {
                        "why": "ss_pred_not_started",
                    }))
            elif ltype == "FF":
                if s_af and p_af:
                    gap = signed_working_minutes(p_af, s_af, scal)
                    if gap is not None and gap < lag:
                        pairs["A1"].append((succ, pred, link, {
                            "why": "ff_before_lag",
                        }))
                elif s_af and not p_af:
                    pairs["A1"].append((succ, pred, link, {
                        "why": "ff_pred_not_finished",
                    }))
            elif ltype == "SF":
                if s_af and p_as:
                    gap = signed_working_minutes(p_as, s_af, scal)
                    if gap is not None and gap < lag:
                        pairs["A1"].append((succ, pred, link, {
                            "why": "sf_before_lag",
                        }))
                elif s_af and not p_as:
                    pairs["A1"].append((succ, pred, link, {
                        "why": "sf_pred_not_started",
                    }))

    for code in ("A1", "A2"):
        seen = set()
        for succ, pred, link, extra in pairs[code]:
            for role, task, other in (("successor", succ, pred), ("predecessor", pred, succ)):
                key = (task["uid"], other["uid"], role)
                if key in seen:
                    continue
                seen.add(key)
                out[code].append(finding(task, code, pair_detail(link, other, role, extra)))

    # ---- Layers 2 and 3.
    for t in tasks:
        if not considered(t):
            continue
        tcal = cal_for(t)
        mpd = day_minutes(t)

        # H: a trend date in the past with no actual behind it, on either end.
        if status is not None:
            s, f = dt(t.get("start")), dt(t.get("finish"))
            why = None
            if s is not None and s < status and not t.get("actual_start"):
                why = "start_elapsed"
            elif f is not None and f < status and not t.get("actual_finish"):
                why = "finish_elapsed"
            if why:
                ref = s if why == "start_elapsed" else f
                out["H"].append(finding(t, "H", {
                    "start": t.get("start"), "finish": t.get("finish"),
                    "status_date": model["project"]["status_date"],
                    "days_elapsed": round(calendar_days(ref, status), 1),
                    "why": why,
                }))

        # E and C: finish variance in WORKING days of the activity's own calendar,
        # so the count agrees with what an in-tool check shows.
        bl = (t.get("baselines") or {}).get(slot) if slot else None
        bf, f = dt((bl or {}).get("finish")), dt(t.get("finish"))
        if bf is not None and f is not None:
            cal = calendar_days(bf, f)
            work = working_days(bf, f, tcal)
            detail = {
                "finish_variance_working_days": work,
                "finish_variance_calendar_days": round(cal, 1),
                "baseline_finish": bl.get("finish"), "finish": t.get("finish"),
                "total_float_days": (
                    round(t["total_slack_minutes"] / mpd, 1)
                    if t.get("total_slack_minutes") is not None else None
                ),
                "percent": physical_pct(t),
                "baseline_slot": slot, "calendar": tcal.name if tcal else None,
            }
            if work is not None:
                if work <= -threshold_days and not t.get("actual_start"):
                    out["E"].append(finding(t, "E", detail))
                elif work >= threshold_days:
                    # Completed activities stay in: consumed delay is information.
                    out["C"].append(finding(t, "C", {
                        **detail, "completed": bool(t.get("actual_finish")),
                    }))

        # G: working time against working time, milestones out.
        s, f = dt(t.get("start")), dt(t.get("finish"))
        dur_min = t.get("duration_minutes")
        if not t.get("milestone") and s and f and dur_min is not None and mpd:
            window_min = tcal.working_minutes(s, f) if tcal else None
            if window_min is None:
                window_min = (working_days(s, f, None) or 0) * mpd
            if abs(dur_min - window_min) > tolerance_days * mpd:
                out["G"].append(finding(t, "G", {
                    "duration_days": round(dur_min / mpd, 2),
                    "window_working_days": round(window_min / mpd, 2),
                    "gap_days": round((dur_min - window_min) / mpd, 2),
                    "calendar": tcal.name if tcal else None,
                    "note": "thermometer: inspect, do not report alone",
                }))

        if t.get("milestone") and not t.get("deadline"):
            out["B"].append(finding(t, "B", {"finish": t.get("finish")}))

        # F: duration-based percent complete, deliberately -- the physical figure
        # belongs to P and to earned value.
        if (t.get("actual_start") and not t.get("actual_finish")
                and (t.get("percent_complete") or 0) == 0):
            out["F"].append(finding(t, "F", {
                "actual_start": t["actual_start"], "percent": t.get("percent_complete"),
            }))

    return {
        "source": model.get("source"),
        "blocking": blocking,
        "conventions": {
            "threshold_days": threshold_days,
            "threshold_basis": "working_days_task_calendar",
            "tolerance_days": tolerance_days,
            "baseline_slot": slot,
            "baseline_slot_basis": (model.get("prevailing_baseline") or {}).get("basis"),
            "calendars_in_file": cal_blob.get("count", 0),
            "calendars_from_file": bool(cals),
            "calendars_in_use": cal_blob.get("in_use", []),
            "link_types_evaluated": link_types_seen,
            "lag_honoured": True,
            "both_complete_pairs_ignored": len(ignored["A1_both_complete"]),
        },
        "counts": summarise(out),
        "findings": out,
        "pairs": {
            code: [
                {"successor_id": s["id"], "successor_uid": s["uid"],
                 "predecessor_id": p["id"], "predecessor_uid": p["uid"],
                 "link_type": l["type"], **extra}
                for s, p, l, extra in pairs[code]
            ] for code in ("A1", "A2")
        },
        "ignored": ignored,
    }


def summarise(out: dict) -> dict:
    """All three defensible counts for network findings, not just one."""
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


CONSOLE = {
    "en": {
        "title": "Schedule integrity review",
        "blocking": "BLOCKING -- the review cannot be trusted until these are fixed:",
        "slot": "Baseline slot used", "threshold": "Threshold",
        "population": "Population", "counting": "Counting",
        "heading": "Findings, in the order the method runs them:",
        "activities": "activities", "as_succ": "as successors", "as_pred": "as predecessors",
        "gate": ["Network findings (A1, A2) gate everything below them. If they are non-zero,",
                 "every forecast date in this file is computed over logic the works does not follow."],
    },
    "pt": {
        "title": "Análise crítica de cronograma",
        "blocking": "IMPEDIMENTO -- a análise não é confiável até isto ser resolvido:",
        "slot": "Gaveta de linha de base usada", "threshold": "Limiar",
        "population": "População", "counting": "Contagem",
        "heading": "Achados, na ordem em que o método os roda:",
        "activities": "atividades", "as_succ": "como sucessoras", "as_pred": "como predecessoras",
        "gate": ["Os achados de rede (A1, A2) condicionam todo o resto. Se não forem zero,",
                 "toda data de tendência deste arquivo é calculada sobre lógica que a obra não segue."],
    },
}


def report(res: dict, lang: str = "en") -> str:
    """The console summary, in the same language as the report."""
    import i18n

    C = CONSOLE.get(lang, CONSOLE["en"])
    CV = i18n.conventions(lang)
    labels = {code: i18n.findings_text(lang)[code][0] for code in ORDER}
    conv = res["conventions"]

    lines = [f"{C['title']} -- {res['source']}", ""]
    if res["blocking"]:
        lines.append(C["blocking"])
        lines += [f"  * {b}" for b in res["blocking"]] + [""]
    lines += [
        f"{C['slot']}: {conv['baseline_slot']} ({CV['slot_basis']})",
        f"{C['threshold']}: {conv['threshold_days']} {CV['threshold_unit']}",
        f"{C['population']}: {CV['population']}",
        f"{C['counting']}: {CV['network_counting']}",
        "",
        C["heading"],
        "",
    ]
    for code in ORDER:
        c = res["counts"][code]
        extra = ""
        if code in ("A1", "A2") and c["marked_rows"]:
            extra = f"  [{C['as_succ']} {c['as_successors']}, {C['as_pred']} {c['as_predecessors']}]"
        lines.append(f"  {code:<3} {c['distinct_activities']:>6} {C['activities']}  {labels[code]}{extra}")
    lines += [""] + C["gate"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model", help="JSON produced by parse_mspdi.py")
    ap.add_argument("--threshold-days", type=int, default=DEFAULT_THRESHOLD_DAYS,
                    help="E and C threshold, in working days of the activity's calendar")
    ap.add_argument("--tolerance-days", type=float, default=DEFAULT_TOLERANCE_DAYS)
    ap.add_argument("--json", help="write the full findings here")
    ap.add_argument("--lang", choices=["en", "pt"],
                    help="force the summary language; by default it follows the schedule")
    args = ap.parse_args()

    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    res = run(model, args.threshold_days, args.tolerance_days)
    import i18n
    lang = args.lang or i18n.detect(model)["lang"]
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, ensure_ascii=False)
        print(f"findings -> {args.json}", file=sys.stderr)
    print(report(res, lang))


if __name__ == "__main__":
    main()
