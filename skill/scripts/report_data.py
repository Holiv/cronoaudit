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

import i18n

# Defaults a profile may override. Severity is a judgement, not a measurement:
# network breaches invalidate every date below them, so they outrank everything.
SEVERITY = {
    "A1": "high", "A2": "high", "H": "high",
    "C": "medium", "E": "medium", "B": "medium", "P": "medium",
    "G": "low", "F": "low",
}
COLUMNS = [
    ("col_row", "id"), ("col_uid", "uid"), ("col_activity", "name"), ("col_wbs", "wbs"),
    ("col_role", "role"), ("col_counterpart", "counterpart_name"), ("col_link", "link_type"),
    ("col_finish", "finish"), ("col_days_elapsed", "days_elapsed"),
    ("col_var_cal", "finish_variance_calendar_days"),
    ("col_var_work", "finish_variance_working_days"),
    ("col_duration", "duration_days"), ("col_window", "window_working_days"),
    ("col_gap", "gap_days"), ("col_calendar", "calendar"),
    ("col_actual_start", "actual_start"), ("col_percent", "percent"),
]
LAYER_KEY = {
    "A1": "net", "A2": "net",
    "H": "date", "E": "date", "C": "date",
    "G": "rep", "B": "rep", "F": "rep", "P": "rep",
}
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


def resolve_grouping(model, field: str) -> dict:
    """Work out what to group by, accepting a custom field by alias or by id.

    Defaults to the top branch of the WBS, which every schedule has. A profile may
    name a custom field instead -- that mapping is the organisation's asset, and the
    transferable idea is that it is declared rather than coded, so one codebase
    serves organisations that keep their meaning in different places.
    """
    if not field or field == "wbs":
        return {"mode": "wbs", "field_id": None, "label": "wbs"}

    fields = (model.get("custom_fields") or {}).get("fields", [])
    wanted = field.strip()
    if wanted.lower().startswith("custom:"):
        wanted = wanted.split(":", 1)[1].strip()

    for row in fields:
        for key in ("field_id", "alias", "field_name"):
            value = row.get(key)
            if value and str(value).strip().lower() == wanted.lower():
                return {
                    "mode": "custom",
                    "field_id": row["field_id"],
                    "label": row.get("alias") or row.get("field_name") or row["field_id"],
                    "fill_rate": row.get("fill_rate"),
                }
    # Named but not found: say so rather than silently grouping everything together.
    return {"mode": "missing", "field_id": None, "label": field}


def group_key(task, grouping: dict):
    """Which bucket this activity reports under."""
    if grouping["mode"] == "custom":
        return str((task.get("custom") or {}).get(grouping["field_id"]) or "(unassigned)")
    if grouping["mode"] == "missing":
        return "(field not found)"
    raw = task.get("outline_number") or task.get("wbs") or ""
    return raw.split(".")[0] or "(unassigned)"


def group_labels(model, grouping: dict):
    """Name each bucket from the summary row that owns it, when there is one."""
    labels = {}
    if grouping["mode"] != "wbs":
        return labels
    for t in model["tasks"]:
        num = t.get("outline_number") or ""
        if t.get("summary") and num and "." not in num:
            labels[num] = t.get("name") or num
    return labels


# Explicit buckets, with the tails clamped. Two things went wrong before this:
# fixed-width bands over a multi-year schedule produced 133 float bands -- a wall of
# rows, not a chart -- and the labels sorted as text, which put "+120" before "+30"
# and made the distribution unreadable. A chart nobody can read is worse than no
# chart, because it still occupies the place where the answer should be.
VARIANCE_EDGES = [-180, -120, -90, -60, -30, -7, 0, 7, 30, 60, 90, 120, 180]
FLOAT_EDGES = [0, 5, 10, 20, 40, 80, 160]


def bucket(value, edges, unit="d"):
    """Place a number in an ordered bucket. Returns (sort_key, label)."""
    if value is None:
        return (len(edges) + 2, "no baseline")
    if value < edges[0]:
        return (0, f"\u2264 {edges[0]:+d} {unit}")
    for i, hi in enumerate(edges[1:], start=1):
        if value < hi:
            return (i, f"{edges[i - 1]:+d} \u2026 {hi:+d} {unit}")
    return (len(edges), f"\u2265 {edges[-1]:+d} {unit}")


def bucket_series(counter_by_key):
    """Order buckets by their numeric position, never by their label text."""
    return [
        {"label": label, "value": count}
        for (_, label), count in sorted(counter_by_key.items(), key=lambda kv: kv[0][0])
    ]


def build_review(model, res, theme=None, grouping="wbs", lang=None) -> dict:
    # The report speaks the schedule's language. Detected from the file's own text
    # rather than configured, because the person running the review is often not the
    # person who wrote the schedule -- and a flag would be wrong as often as right.
    detected = i18n.detect(model)
    lang = lang or detected["lang"]
    L = i18n.ui(lang)
    FT = i18n.findings_text(lang)
    LY = i18n.layers(lang)
    SW = i18n.severity_words(lang)
    CV = i18n.conventions(lang)

    lv = leaves(model)
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    grp = resolve_grouping(model, grouping)
    labels = group_labels(model, grp)

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
        title, subtitle, criterion, source, reproduce = FT[code]
        findings.append({
            "code": code,
            "layer": LY[LAYER_KEY[code]],
            "severity": SEVERITY[code],
            "severity_word": SW[SEVERITY[code]],
            "title": title,
            "subtitle": subtitle,
            "criterion": criterion,
            "source": source,
            "reproduce": reproduce,
            "count": counts["distinct_activities"],
            "rows": counts["marked_rows"],
            "as_successors": counts.get("as_successors"),
            "as_predecessors": counts.get("as_predecessors"),
            "columns": [{"label": L[h], "key": k} for h, k in used],
            "items": items,
        })

    # ---- charts, all computable from a plain export with no custom field
    var_hist: dict = {}
    floats: dict = {}
    starts = OrderedDict()
    groups = OrderedDict()

    for t in lv:
        bl = (t.get("baselines") or {}).get(slot) or {}
        bf, f = dt(bl.get("finish")), dt(t.get("finish"))
        if bf and f:
            key = bucket(int((f - bf).days), VARIANCE_EDGES)
            var_hist[key] = var_hist.get(key, 0) + 1

        sl = t.get("total_slack_minutes")
        mpd = (model.get("units") or {}).get("minutes_per_day") or 480
        if sl is not None:
            key = bucket(int(sl / mpd), FLOAT_EDGES)
            floats[key] = floats.get(key, 0) + 1

        s = dt(t.get("start"))
        if s:
            k = s.strftime("%Y-%m")
            starts[k] = starts.get(k, 0) + 1

        gk = group_key(t, grp)
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
    # One bucket holding everything is not a distribution. Say so and point at the
    # discovery step, rather than presenting a single 100% bar as an analysis.
    grouping_uninformative = len(group_rows) < 2

    def series(d):
        """Chronological for YYYY-MM keys, which sort correctly as text."""
        return [{"label": k, "value": v} for k, v in sorted(d.items())]

    return {
        "kind": "review",
        "lang": lang,
        "labels": L,
        "language": detected,
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
            "grouping": grp["label"],
            "grouping_mode": grp["mode"],
            "grouping_uninformative": grouping_uninformative,
            "calendars_in_file": (model.get("calendars") or {}).get("count", 0),
        },
        "calendars": (model.get("calendars") or {}).get("in_use", []),
        "conventions": {
            **res["conventions"],
            "threshold_unit": CV["threshold_unit"],
            "baseline_slot_basis": CV["slot_basis"],
            "population": CV["population"],
            "network_counting": CV["network_counting"],
            "working_days": CV["working_calendar"] if res["conventions"].get("calendars_from_file")
            else CV["working_fallback"],
            "percent_source": CV["percent_source"],
            "tolerance_text": CV["tolerance"].format(n=res["conventions"]["tolerance_days"]),
        },
        "blocking": res.get("blocking", []),
        "findings": findings,
        "charts": {
            "variance_histogram": bucket_series(var_hist),
            "float_bands": bucket_series(floats),
            "starts_per_month": series(starts),
            "by_group": group_rows,
        },
    }


def build_cycle(cmp_res, theme=None, lang=None, detected=None) -> dict:
    lang = lang or (detected or {}).get("lang") or "en"
    return {
        "kind": "cycle",
        "lang": lang,
        "labels": i18n.ui(lang),
        "language": detected or {"lang": lang, "confidence": "inherited"},
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            **{f"previous_{k}": v for k, v in cmp_res["previous"].items()},
            **{f"current_{k}": v for k, v in cmp_res["current"].items()},
            "movement_points": cmp_res.get("movement_points"),
            "explained_points": cmp_res.get("decomposition_sums_to_points"),
            "unexplained_points": cmp_res.get("movement_unexplained_points"),
        },
        "conventions": {
            **cmp_res["conventions"],
            "denominator": i18n.conventions(lang)["denominator"],
        },
        "warnings": cmp_res.get("warnings", []),
        "readings": {
            "execution": [t for t in cmp_res["trend"] if t["reading"] == "execution"],
            "replan": [t for t in cmp_res["trend"] if t["reading"] == "replan"],
            "reference": cmp_res["baseline_moved"],
        },
        "decomposition": cmp_res["decomposition"],
        "unmatched": cmp_res["unmatched"],
    }
