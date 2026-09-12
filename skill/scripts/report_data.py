#!/usr/bin/env python3
"""Build the JSON payload a report template consumes.

The contract mirrors a mature in-tool implementation: the template carries a
`/*DATA*/` marker and this module produces what replaces it. Data and presentation
stay separate, so anyone can restyle the report without touching Python, and the
payload can feed a spreadsheet or a dashboard instead.

Every default here is overridable by an organisation profile. Nothing in this file
reads a company-specific field name: the grouping field defaults to the WBS branch,
which every schedule has, and the extra columns come from what the discovery step
found, never from a name assumed in advance.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime

import custom_fields as cf_mod
import explain as ex_mod
import i18n
import narrative as narrative_mod

# Severity is a judgement, not a measurement: network breaches invalidate every
# date below them, so they outrank everything. Four named levels, as the in-tool
# report uses, not three generic ones.
SEVERITY = {
    "A1": "critical", "A2": "critical",
    "H": "high", "E": "high", "C": "high", "B": "high",
    "G": "check", "F": "check",
    "P": "pending",
}
LAYER_KEY = {
    "A1": "net", "A2": "net",
    "H": "date", "E": "date", "C": "date",
    "G": "rep", "B": "rep", "F": "rep", "P": "rep",
}
ORDER = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]

# The bands the in-tool report uses, adopted so the two reports compare line by
# line. Working days of the activity's own calendar.
VARIANCE_BANDS = [
    ("≤ -90", lambda v: v <= -90), ("-89 … -30", lambda v: -90 < v <= -30),
    ("-29 … -10", lambda v: -30 < v <= -10), ("-9 … -1", lambda v: -10 < v < 0),
    ("0", lambda v: v == 0), ("1 … 9", lambda v: 0 < v < 10),
    ("10 … 29", lambda v: 10 <= v < 30), ("≥ 30", lambda v: v >= 30),
]
FLOAT_BANDS = [
    ("≤ 0", lambda v: v <= 0), ("1 … 9", lambda v: 0 < v < 10),
    ("10 … 29", lambda v: 10 <= v < 30), ("30 … 89", lambda v: 30 <= v < 90),
    ("≥ 90", lambda v: v >= 90),
]

DEFAULT_THEME = {
    "accent": "#1B4D8F", "crit": "#A32015", "warn": "#8A5300", "good": "#166B50",
    "font_display": "", "font_sans": "", "font_mono": "", "logo_text": "",
}


def dt(v):
    return datetime.fromisoformat(v) if v else None


def fmt_date(v, lang):
    d = dt(v)
    if d is None:
        return None
    return d.strftime("%d/%m/%Y") if lang == "pt" else d.strftime("%Y-%m-%d")


def leaves(model):
    return [
        t for t in model["tasks"]
        if not t.get("summary") and t.get("active") is not False and not t.get("external")
    ]


def resolve_grouping(model, field: str) -> dict:
    """Work out what to group by, accepting a custom field by alias, name or id."""
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
                return {"mode": "custom", "field_id": row["field_id"],
                        "label": row.get("alias") or row.get("field_name") or row["field_id"]}
    return {"mode": "missing", "field_id": None, "label": field}


def group_key(task, grouping: dict):
    if grouping["mode"] == "custom":
        return str((task.get("custom") or {}).get(grouping["field_id"]) or "(unassigned)")
    if grouping["mode"] == "missing":
        return "(field not found)"
    raw = task.get("outline_number") or task.get("wbs") or ""
    return raw.split(".")[0] or "(unassigned)"


def group_labels(model, grouping: dict):
    labels = {}
    if grouping["mode"] != "wbs":
        return labels
    for t in model["tasks"]:
        num = t.get("outline_number") or ""
        if t.get("summary") and num and "." not in num:
            labels[num] = t.get("name") or num
    return labels


def band_of(value, bands):
    for label, test in bands:
        if test(value):
            return label
    return bands[-1][0]


def band_series(counter, bands):
    return [{"label": label, "value": counter.get(label, 0)} for label, _ in bands]


def pct_of(task):
    p = task.get("physical_percent_complete")
    return p if p is not None else (task.get("percent_complete") or 0.0)


def discovered_columns(model, grouping: dict, L: dict) -> list:
    """Extra columns the organisation's own fields can supply, when well filled.

    Discipline, service and section are what a planner reads first on a row. They
    come from discovery, never from a field name assumed in advance, and only when
    the field is filled on most activities -- a column that is mostly blank is noise.
    """
    disc = model.get("custom_fields") or {}
    cands, _ = cf_mod.interview_candidates(disc, min_fill=80.0)
    cols = []
    seen = set()
    for role, label_key in (("discipline", "col_discipline"), ("work_front", "col_section"),
                            ("regulator_code", "col_section")):
        items = cands.get(role) or []
        items = [i for i in items if i["closed_set"]]
        if not items:
            continue
        fid = items[0]["field_id"]
        if fid in seen or fid == grouping.get("field_id"):
            continue
        seen.add(fid)
        cols.append({"key": f"cf_{fid}", "field_id": fid,
                     "label": items[0]["alias"] or L[label_key]})
    return cols


def build_review(model, res, theme=None, grouping="wbs", lang=None, phasing=None,
                 productivity=None, quality=None, forecast=None, forensics=None) -> dict:
    detected = i18n.detect(model)
    lang = lang or detected["lang"]
    L = i18n.ui(lang)
    FT = i18n.findings_text(lang)
    LY = i18n.layers(lang)
    SW = i18n.severity_words(lang)
    CV = i18n.conventions(lang)
    EX = ex_mod.explain(lang)

    import calendars as cal_mod
    lv = leaves(model)
    by_uid = {t["uid"]: t for t in model["tasks"]}
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal = cal_blob.get("default_uid")
    grp = resolve_grouping(model, grouping)
    labels = group_labels(model, grp)
    extra_cols = discovered_columns(model, grp, L)
    conv = res["conventions"]

    def day_minutes(task):
        cal_uid = task.get("calendar_uid")
        for c in (model.get("calendars") or {}).get("in_use", []):
            if c["uid"] == cal_uid:
                return c["hours_per_day"] * 60.0
        return (model.get("units") or {}).get("minutes_per_day") or 480.0

    def bl_of(task):
        return (task.get("baselines") or {}).get(slot) or {} if slot else {}

    # ---- earned value: ours, and the tool's own, side by side
    budget = earned = earned_file = planned_file = 0.0
    compared = matches = 0
    ahead_of_baseline = []   # executed before the baseline window; the tool credits nothing yet
    unexplained = []
    status = dt(model["project"].get("status_date"))
    for t in lv:
        cost = bl_of(t).get("cost") or 0.0
        if cost <= 0:
            continue
        budget += cost
        mine = cost * pct_of(t) / 100.0
        earned += mine
        if t.get("bcwp") is not None:
            compared += 1
            earned_file += t["bcwp"]
            if abs(mine - t["bcwp"]) < 0.01:
                matches += 1
            else:
                bstart = dt(bl_of(t).get("start"))
                if status is not None and bstart is not None and bstart > status:
                    # The tool's earned value is the time-phased baseline cost credited
                    # up to the status date. Work done BEFORE its baseline window has
                    # no baseline cost phased before the status date, so the tool
                    # credits nothing until the calendar reaches the window -- while
                    # the method credits cost x physical percent at once. Both are
                    # right against their own instant; this is the datum family.
                    ahead_of_baseline.append({
                        "id": t["id"], "name": t["name"], "cost": cost,
                        "percent": pct_of(t), "file_bcwp": t["bcwp"],
                        "baseline_start": bl_of(t).get("start"),
                    })
                else:
                    unexplained.append({"id": t["id"], "name": t["name"], "cost": cost,
                                        "mine": round(mine, 2), "file_bcwp": t["bcwp"]})
        if t.get("bcws") is not None:
            planned_file += t["bcws"]

    # ---- findings, enriched with the columns a planner reads
    marked = {code: {f["uid"] for f in res["findings"][code]} for code in ORDER}
    pred_ids = {t["uid"]: ", ".join(
        str(by_uid[l["predecessor_uid"]]["id"]) for l in (t.get("predecessors") or [])
        if l["predecessor_uid"] in by_uid) for t in model["tasks"]}

    def enrich(item):
        t = by_uid[item["uid"]]
        bl = bl_of(t)
        mpd = day_minutes(t)
        var_d = item.get("finish_variance_working_days")
        if var_d is None and bl.get("finish") and t.get("finish"):
            cal = cals.get(t.get("calendar_uid")) or cals.get(default_cal)
            var_d = (cal.working_days(dt(bl["finish"]), dt(t["finish"])) if cal
                     else round((dt(t["finish"]) - dt(bl["finish"])).days * 5 / 7))
        row = {
            "id": t["id"], "name": t["name"],
            "term_lb": fmt_date(bl.get("finish"), lang), "term": fmt_date(t.get("finish"), lang),
            "var_d": var_d,
            "float_d": (round(t["total_slack_minutes"] / mpd, 1)
                        if t.get("total_slack_minutes") is not None else None),
            "real_pct": pct_of(t),
            "pred": pred_ids.get(t["uid"]) or "",
        }
        for c in extra_cols:
            row[c["key"]] = (t.get("custom") or {}).get(c["field_id"])
        if item.get("role"):
            succ_id = item["id"] if item["role"] == "successor" else item["counterpart_id"]
            pred_id = item["counterpart_id"] if item["role"] == "successor" else item["id"]
            row["pair"] = L["pair_fmt"].format(succ=succ_id, pred=pred_id)
            row["role"] = item["role"]
            row["link"] = i18n.link_type(lang, item.get("link_type", "FS"))
        for k in ("days_elapsed", "duration_days", "window_working_days", "gap_days",
                  "percent", "overlap_beyond_lead_days", "completed"):
            if k in item and item[k] is not None:
                row[k] = item[k]
        if item.get("why"):
            row["why"] = i18n.why(lang, item["why"])
        return row

    findings = []
    for code in ORDER:
        items = [enrich(i) for i in res["findings"][code]]
        counts = res["counts"][code]
        cols = [{"label": L["col_row"], "key": "id"}, {"label": L["col_activity"], "key": "name"}]
        if code in ("A1", "A2"):
            cols += [{"label": L["col_pair"], "key": "pair"}, {"label": L["col_link"], "key": "link"},
                     {"label": L["col_why"], "key": "why"}]
        cols += [{"label": c["label"], "key": c["key"]} for c in extra_cols]
        cols += [{"label": L["col_term_lb"], "key": "term_lb"}, {"label": L["col_term"], "key": "term"},
                 {"label": L["col_var"], "key": "var_d"}, {"label": L["col_float"], "key": "float_d"},
                 {"label": L["col_real_pct"], "key": "real_pct"}]
        if code == "G":
            cols += [{"label": L["col_duration"], "key": "duration_days"},
                     {"label": L["col_window"], "key": "window_working_days"},
                     {"label": L["col_gap"], "key": "gap_days"}]
        if code == "H":
            cols += [{"label": L["col_days_elapsed"], "key": "days_elapsed"},
                     {"label": L["col_why"], "key": "why"}]
        if code not in ("A1", "A2"):
            cols += [{"label": L["col_pred"], "key": "pred"}]
        title, subtitle, criterion, source, reproduce = FT[code]
        problem, impact, solution = EX[code]
        findings.append({
            "code": code, "layer": LY[LAYER_KEY[code]],
            "severity": SEVERITY[code], "severity_word": SW[SEVERITY[code]],
            "title": title, "subtitle": subtitle, "criterion": criterion,
            "source": source, "reproduce": reproduce,
            "problem": problem, "impact": impact, "solution": solution,
            "count": counts["distinct_activities"], "rows": counts["marked_rows"],
            "as_successors": counts.get("as_successors"),
            "as_predecessors": counts.get("as_predecessors"),
            "columns": cols, "items": items,
        })

    # ---- charts
    var_c, float_c, starts = {}, {}, OrderedDict()
    groups = OrderedDict()
    for t in lv:
        bl = bl_of(t)
        mpd = day_minutes(t)
        f_item = next((i for i in res["findings"]["C"] + res["findings"]["E"]
                       if i["uid"] == t["uid"]), None)
        var = f_item.get("finish_variance_working_days") if f_item else None
        if var is None and bl.get("finish") and t.get("finish"):
            # Not in E or C: variance is inside the threshold. Calendar days here
            # would mix units, so approximate with calendar days / 7 * 6 is wrong;
            # take the calendar-day figure only for banding position near zero.
            var = round((dt(t["finish"]) - dt(bl["finish"])).days * 5 / 7)
        if var is not None:
            k = band_of(var, VARIANCE_BANDS)
            var_c[k] = var_c.get(k, 0) + 1
        if t.get("total_slack_minutes") is not None:
            k = band_of(t["total_slack_minutes"] / mpd, FLOAT_BANDS)
            float_c[k] = float_c.get(k, 0) + 1
        s = dt(t.get("start"))
        if s:
            k = s.strftime("%Y-%m")
            starts[k] = starts.get(k, 0) + 1

        gk = group_key(t, grp)
        g = groups.setdefault(gk, {
            "label": labels.get(gk, gk), "activities": 0, "budget": 0.0,
            "earned": 0.0, "planned": 0.0, "findings": {c: 0 for c in ORDER},
        })
        g["activities"] += 1
        cost = bl.get("cost") or 0.0
        if cost > 0:
            g["budget"] += cost
            g["earned"] += cost * pct_of(t) / 100.0
            g["planned"] += t.get("bcws") or 0.0
        for c in ORDER:
            if t["uid"] in marked[c]:
                g["findings"][c] += 1

    group_rows = []
    for g in groups.values():
        b = g["budget"]
        group_rows.append({
            "label": g["label"], "activities": g["activities"], "budget": round(b, 2),
            "weight_pct": round(b / budget * 100, 2) if budget else 0.0,
            "planned_pct": round(g["planned"] / b * 100, 2) if b else 0.0,
            "earned_pct": round(g["earned"] / b * 100, 2) if b else 0.0,
            "findings": g["findings"], "finding_total": sum(g["findings"].values()),
        })
    group_rows.sort(key=lambda r: r["weight_pct"], reverse=True)

    lt = conv.get("link_types_evaluated") or {}
    links_text = L["links_evaluated"].format(list=", ".join(
        f"{i18n.link_type(lang, k)} {v}" for k, v in lt.items() if v))

    payload = {
        "kind": "review", "lang": lang, "labels": L, "language": detected,
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "title": model["project"].get("title") or model["project"].get("name") or "Schedule",
            "file": model.get("source"),
            "status_date": fmt_date(model["project"].get("status_date"), lang),
            "generated": datetime.now().strftime("%d/%m/%Y %H:%M" if lang == "pt" else "%Y-%m-%d %H:%M"),
            "tasks": model["counts"]["tasks"], "leaves": len(lv),
            "budget": round(budget, 2),
            "percent_earned": round(earned / budget * 100, 2) if budget else None,
            "percent_planned_file": round(planned_file / budget * 100, 2) if budget else None,
            "reconciliation": {
                "leaves_compared": compared, "matches_to_cent": matches,
                "ahead_of_baseline": len(ahead_of_baseline),
                "ahead_of_baseline_value": round(sum(x["cost"] for x in ahead_of_baseline), 2),
                "ahead_of_baseline_items": ahead_of_baseline[:20],
                "unexplained": len(unexplained),
                "unexplained_items": unexplained[:20],
                "earned_computed": round(earned, 2), "earned_file": round(earned_file, 2),
                "difference": round(earned - earned_file, 2),
                "ev_method": {1: "physical", 0: "percent"}.get(
                    model["project"].get("default_ev_method"), "unknown"),
            },
            "baseline_slot": slot,
            "with_physical_percent": model["counts"].get("with_physical_percent"),
            "grouping": grp["label"], "grouping_mode": grp["mode"],
            "grouping_uninformative": len(group_rows) < 2,
            "calendars_in_file": (model.get("calendars") or {}).get("count", 0),
            "ignored_pairs": conv.get("both_complete_pairs_ignored", 0),
            "links_evaluated": links_text,
        },
        "conventions": {
            **conv,
            "threshold_unit": CV["threshold_unit"], "baseline_slot_basis": CV["slot_basis"],
            "population": CV["population"], "network_counting": CV["network_counting"],
            "working_days": CV["working_calendar"] if conv.get("calendars_from_file")
            else CV["working_fallback"],
            "percent_source": CV["percent_source"],
            "tolerance_text": CV["tolerance"].format(n=conv["tolerance_days"]),
        },
        "blocking": res.get("blocking", []),
        "findings": findings,
        "charts": {
            "variance_histogram": band_series(var_c, VARIANCE_BANDS),
            "float_bands": band_series(float_c, FLOAT_BANDS),
            "starts_per_month": [{"label": k, "value": v} for k, v in sorted(starts.items())],
            "by_group": group_rows,
        },
        "calendars": (model.get("calendars") or {}).get("in_use", []),
        "scurve": phasing,
        "productivity": productivity,
        "quality": localize_quality(quality, lang) if quality else None,
        "forecast": forecast,
        "forensics": forensics,
        # The executive synthesis is injected later by whoever writes it; the slot
        # exists so the template knows where it goes and how to label it.
        "narrative": None,
    }
    payload["readings"] = narrative_mod.build(payload, lang)
    return payload


def localize_quality(q: dict, lang: str) -> dict:
    QT = i18n.quality_text(lang)
    out = dict(q)
    out["metrics"] = [
        {**m, "title": QT.get(m["code"], (m["code"], ""))[0],
         "description": QT.get(m["code"], (m["code"], ""))[1]}
        for m in q.get("metrics", [])
    ]
    return out


def build_cycle(cmp_res, theme=None, lang=None, detected=None) -> dict:
    lang = lang or (detected or {}).get("lang") or "en"
    return {
        "kind": "cycle", "lang": lang, "labels": i18n.ui(lang),
        "language": detected or {"lang": lang, "confidence": "inherited"},
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "generated": datetime.now().strftime("%d/%m/%Y %H:%M" if lang == "pt" else "%Y-%m-%d %H:%M"),
            **{f"previous_{k}": v for k, v in cmp_res["previous"].items()},
            **{f"current_{k}": v for k, v in cmp_res["current"].items()},
            "movement_points": cmp_res.get("movement_points"),
            "explained_points": cmp_res.get("decomposition_sums_to_points"),
            "unexplained_points": cmp_res.get("movement_unexplained_points"),
        },
        "conventions": {**cmp_res["conventions"],
                        "denominator": i18n.conventions(lang)["denominator"]},
        "warnings": cmp_res.get("warnings", []),
        "readings": {
            "execution": [t for t in cmp_res["trend"] if t["reading"] == "execution"],
            "replan": [t for t in cmp_res["trend"] if t["reading"] == "replan"],
            "reference": cmp_res["baseline_moved"],
        },
        "decomposition": cmp_res["decomposition"],
        "unmatched": cmp_res["unmatched"],
    }
