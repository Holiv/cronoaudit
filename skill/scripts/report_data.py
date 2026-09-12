#!/usr/bin/env python3
"""Build the JSON payload a report template consumes.

The contract is deliberately the same shape as a mature in-tool implementation:
the template carries a `/*DATA*/` marker and this module produces what replaces
it. Data and presentation stay separate, so anyone can restyle the report without
touching Python, and the payload can feed a spreadsheet or a dashboard instead.

Every default here is overridable by an organisation profile. Nothing in this file
reads a company-specific field name: the grouping field defaults to the WBS branch,
which every schedule has, and a profile can point it at a custom field instead.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime

# Defaults a profile may override. Severity is a judgement, not a measurement:
# network breaches invalidate every date below them, so they outrank everything.
SEVERITY = {
    "A1": "high", "A2": "high", "H": "high",
    "C": "medium", "E": "medium", "B": "medium", "P": "medium",
    "G": "low", "F": "low",
}
LAYER = {
    "A1": "Network integrity", "A2": "Network integrity",
    "H": "Date adherence", "E": "Date adherence", "C": "Date adherence",
    "G": "Reporting consistency", "B": "Reporting consistency",
    "F": "Reporting consistency", "P": "Reporting consistency",
}
TITLE = {
    "A1": "Execution out of sequence",
    "A2": "Total inversion",
    "H": "Trend elapsed with no progress",
    "E": "Pulled forward and never started",
    "C": "Delayed beyond the threshold",
    "G": "Duration incompatible with the window",
    "B": "Milestone with no deadline",
    "F": "In progress at zero percent",
    "P": "Pending record",
}
SUBTITLE = {
    "A1": "A successor started before its predecessor finished",
    "A2": "A successor is complete while its predecessor never started",
    "H": "Dates in the past that never happened",
    "E": "The forecast moved earlier with no execution behind it",
    "C": "Material slippage against the baseline",
    "F": "Started, but reporting no progress at all",
    "G": "Thermometer of reprogramming, not a finding on its own",
    "B": "Nothing in the file makes this date binding",
    "P": "One hundred percent physical with no actual finish",
}
CRITERION = {
    "A1": "Successor has an actual start; the predecessor has no actual finish. "
          "Both ends of the violated link are listed.",
    "A2": "Successor has an actual finish; the predecessor has no actual start.",
    "H": "Finish is earlier than the status date, with neither an actual start nor "
         "an actual finish.",
    "E": "Finish minus baseline finish is at or below minus the threshold, and there "
         "is no actual start.",
    "C": "Finish minus baseline finish is at or above the threshold.",
    "G": "Duration converted to days against the file's minutes-per-day differs from "
         "the working days between start and finish by more than the tolerance.",
    "B": "The task is a milestone and no deadline is set.",
    "F": "There is an actual start, no actual finish, and percent complete is zero.",
    "P": "Percent complete is one hundred and there is no actual finish.",
}
SOURCE = {
    "A1": "Actual Start, predecessor Actual Finish, Predecessor Link",
    "A2": "Actual Finish, predecessor Actual Start, Predecessor Link",
    "H": "Finish, Actual Start, Actual Finish, project Status Date",
    "E": "Finish, Baseline Finish, Actual Start, and the activity's own Calendar column",
    "C": "Finish, Baseline Finish, and the activity's own Calendar column",
    "G": "Duration, Start, Finish, and the activity's own Calendar column",
    "B": "Milestone, Deadline",
    "F": "Actual Start, Actual Finish, Percent Complete",
    "P": "Physical Percent Complete, Actual Finish",
}
REPRODUCE = {
    "A1": "Group by predecessor and filter on Actual Start present. In the schedule, "
          "flag the pair and inspect the link in the Gantt.",
    "A2": "Filter Actual Finish present, then check each predecessor's Actual Start.",
    "H": "Insert the Status Date field, filter Finish before it, and add Actual Start "
         "and Actual Finish as columns to confirm both are blank.",
    "E": "Insert Finish Variance. Filter at or below minus the threshold with Actual "
         "Start blank.",
    "C": "Insert Finish Variance and filter at or above the threshold.",
    "G": "Show Duration, Start, Finish and Calendar side by side. The span must be "
         "measured in that calendar's working time, not in days.",
    "B": "Filter on Milestone, insert the Deadline column, and sort by it.",
    "F": "Filter Actual Start present and Percent Complete equal to zero.",
    "P": "Insert Physical Percent Complete and Actual Finish, and filter one hundred "
         "with the finish blank.",
}
COLUMNS = [
    ("Row", "id"), ("UID", "uid"), ("Activity", "name"), ("WBS", "wbs"),
    ("Role", "role"), ("Counterpart", "counterpart_name"), ("Link", "link_type"),
    ("Finish", "finish"), ("Days elapsed", "days_elapsed"),
    ("Var. calendar d", "finish_variance_calendar_days"),
    ("Var. working d", "finish_variance_working_days"),
    ("Duration d", "duration_days"), ("Window wd", "window_working_days"),
    ("Gap d", "gap_days"), ("Calendar", "calendar"),
    ("Actual start", "actual_start"), ("Percent", "percent"),
]
ORDER = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]

DEFAULT_THEME = {
    "accent": "#1f4e5f",
    "high": "#9c3b2e",
    "medium": "#8a6a1e",
    "low": "#3f6b57",
    "font_sans": '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    "font_mono": 'ui-monospace,SFMono-Regular,Menlo,Consolas,monospace',
    "logo_text": "",
}


def dt(v):
    return datetime.fromisoformat(v) if v else None


def leaves(model):
    return [
        t for t in model["tasks"]
        if not t.get("summary") and t.get("active") is not False and not t.get("external")
    ]


def group_key(task, field: str):
    """Which bucket this activity reports under.

    Defaults to the top branch of the WBS, which every schedule has. A profile may
    name a custom field instead -- that mapping is the organisation's asset, and the
    transferable idea is that it is declared rather than coded.
    """
    if field == "wbs":
        raw = task.get("outline_number") or task.get("wbs") or ""
        return raw.split(".")[0] or "(unassigned)"
    return str(task.get(field) or "(unassigned)")


def group_labels(model, field: str):
    """Name each bucket from the summary row that owns it, when there is one."""
    labels = {}
    if field != "wbs":
        return labels
    for t in model["tasks"]:
        num = t.get("outline_number") or ""
        if t.get("summary") and num and "." not in num:
            labels[num] = t.get("name") or num
    return labels


def band(value, width, unit="d"):
    """Bucket a signed number into fixed-width bands, labelled readably."""
    if value is None:
        return "no baseline"
    lo = int(value // width) * width
    return f"{lo:+d} to {lo + width:+d} {unit}"


def build_review(model, res, theme=None, grouping="wbs") -> dict:
    lv = leaves(model)
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    labels = group_labels(model, grouping)

    budget = earned = 0.0
    for t in lv:
        bl = (t.get("baselines") or {}).get(slot) or {}
        cost = bl.get("cost") or 0.0
        if cost <= 0:
            continue
        phys = t.get("physical_percent_complete")
        if phys is None:
            phys = t.get("percent_complete") or 0.0
        budget += cost
        earned += cost * phys / 100.0

    # ---- findings, in the order the method runs them
    findings = []
    marked = {code: {f["uid"] for f in res["findings"][code]} for code in ORDER}
    for code in ORDER:
        items = res["findings"][code]
        counts = res["counts"][code]
        used = [(h, k) for h, k in COLUMNS if any(k in i for i in items)]
        findings.append({
            "code": code,
            "layer": LAYER[code],
            "severity": SEVERITY[code],
            "title": TITLE[code],
            "subtitle": SUBTITLE[code],
            "criterion": CRITERION[code],
            "source": SOURCE[code],
            "reproduce": REPRODUCE[code],
            "count": counts["distinct_activities"],
            "rows": counts["marked_rows"],
            "as_successors": counts.get("as_successors"),
            "as_predecessors": counts.get("as_predecessors"),
            "columns": [{"label": h, "key": k} for h, k in used],
            "items": items,
        })

    # ---- charts, all computable from a plain export with no custom field
    var_hist = OrderedDict()
    floats = OrderedDict()
    starts = OrderedDict()
    groups = OrderedDict()

    for t in lv:
        bl = (t.get("baselines") or {}).get(slot) or {}
        bf, f = dt(bl.get("finish")), dt(t.get("finish"))
        if bf and f:
            key = band(int((f - bf).days), 30)
            var_hist[key] = var_hist.get(key, 0) + 1

        sl = t.get("total_slack_minutes")
        mpd = (model.get("units") or {}).get("minutes_per_day") or 480
        if sl is not None:
            floats[band(int(sl / mpd), 10)] = floats.get(band(int(sl / mpd), 10), 0) + 1

        s = dt(t.get("start"))
        if s:
            k = s.strftime("%Y-%m")
            starts[k] = starts.get(k, 0) + 1

        gk = group_key(t, grouping)
        g = groups.setdefault(gk, {
            "key": gk, "label": labels.get(gk, gk), "budget": 0.0, "earned": 0.0,
            "activities": 0, "findings": {c: 0 for c in ORDER},
        })
        g["activities"] += 1
        cost = bl.get("cost") or 0.0
        if cost > 0:
            phys = t.get("physical_percent_complete")
            if phys is None:
                phys = t.get("percent_complete") or 0.0
            g["budget"] += cost
            g["earned"] += cost * phys / 100.0
        for c in ORDER:
            if t["uid"] in marked[c]:
                g["findings"][c] += 1

    group_rows = []
    for g in groups.values():
        group_rows.append({
            "label": g["label"],
            "key": g["key"],
            "activities": g["activities"],
            "budget": round(g["budget"], 2),
            "weight_pct": round(g["budget"] / budget * 100, 2) if budget else 0.0,
            "earned_pct": round(g["earned"] / g["budget"] * 100, 2) if g["budget"] else 0.0,
            "findings": g["findings"],
            "finding_total": sum(g["findings"].values()),
        })
    group_rows.sort(key=lambda r: r["weight_pct"], reverse=True)

    def series(d, sort_numeric=False):
        items = list(d.items())
        items.sort(key=lambda kv: kv[0])
        return [{"label": k, "value": v} for k, v in items]

    return {
        "kind": "review",
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "title": model["project"].get("title") or model["project"].get("name") or "Schedule",
            "file": model.get("source"),
            "status_date": model["project"].get("status_date"),
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tasks": model["counts"]["tasks"],
            "leaves": len(lv),
            "budget": round(budget, 2),
            "percent_earned": round(earned / budget * 100, 2) if budget else None,
            "baseline_slot": slot,
            "with_physical_percent": model["counts"].get("with_physical_percent"),
            "grouping": grouping,
            "calendars_in_file": (model.get("calendars") or {}).get("count", 0),
        },
        "calendars": (model.get("calendars") or {}).get("in_use", []),
        "conventions": res["conventions"],
        "blocking": res.get("blocking", []),
        "findings": findings,
        "charts": {
            "variance_histogram": series(var_hist),
            "float_bands": series(floats),
            "starts_per_month": series(starts),
            "by_group": group_rows,
        },
    }


def build_cycle(cmp_res, theme=None) -> dict:
    return {
        "kind": "cycle",
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            **{f"previous_{k}": v for k, v in cmp_res["previous"].items()},
            **{f"current_{k}": v for k, v in cmp_res["current"].items()},
            "movement_points": cmp_res.get("movement_points"),
            "explained_points": cmp_res.get("decomposition_sums_to_points"),
            "unexplained_points": cmp_res.get("movement_unexplained_points"),
        },
        "conventions": cmp_res["conventions"],
        "warnings": cmp_res.get("warnings", []),
        "readings": {
            "execution": [t for t in cmp_res["trend"] if t["reading"] == "execution"],
            "replan": [t for t in cmp_res["trend"] if t["reading"] == "replan"],
            "reference": cmp_res["baseline_moved"],
        },
        "decomposition": cmp_res["decomposition"],
        "unmatched": cmp_res["unmatched"],
    }
