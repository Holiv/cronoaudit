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

import os
from collections import OrderedDict
from datetime import datetime

import custom_fields as cf_mod
import explain as ex_mod
import i18n
import narrative as narrative_mod
import network_quality as quality_mod
import parse_mspdi as mspdi
import profile as prof_mod

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


def network_state(model, quality=None) -> dict:
    """Whether there is a network for "the network holds" to be said about.

    Zero out-of-sequence findings prove something only when activities are
    linked. This reads the two figures that decide it from the network-quality
    implementation (called here when the caller has not run it): the number of
    links, and the missing-logic metric with its own quoted threshold.
      none    no activity is linked to another
      open    linked, but missing logic is above the threshold
      linked  linked, and missing logic within it
    """
    q = quality or quality_mod.build(model)
    q1 = next((m for m in q.get("metrics", []) if m["code"] == "Q1"), None) or {}
    links = (q.get("population") or {}).get("links") or 0
    share, threshold = q1.get("share_pct"), q1.get("threshold_pct")
    if links == 0:
        state = "none"
    elif share is not None and threshold is not None and share > threshold:
        state = "open"
    else:
        state = "linked"
    return {"state": state, "links": links, "open": q1.get("population") or 0,
            "unlinked": q1.get("count") or 0, "share_pct": share, "threshold_pct": threshold,
            "basis": "links between leaf activities; missing logic (Q1) = open activities with "
                     "no predecessor or no successor, against its quoted threshold"}


# How many out-of-sequence pairs, off the critical path and off the chain that
# drives the project finish, are NAMED rather than read as a broken network.
# Ours, not a published threshold: one or two pairs on a side branch do not make
# every date in the file derive from logic the works ignores; four or more read
# as a practice, not an incident. Total inversion (A2) is never scaled.
GATE_MAX_PAIRS = 3


def network_gate(model, res, forensics=None) -> dict:
    """How far the violated logic reaches, so the warning is as wide as the breach.

    absolute  A2 present, more than GATE_MAX_PAIRS pairs, or a pair touching an
              unfinished critical activity (the tool's flag, or total float at or
              below zero) or the chain that drives the project finish
    scoped    otherwise: the pairs are named, and the milestones whose driving
              chain passes through them (from the forensics, when run)
    none      no A1 or A2 pair
    """
    import calendars as cal_mod
    import forensics as fx_mod
    pairs = (res.get("pairs") or {}).get("A1") or []
    a2 = (res.get("counts") or {}).get("A2", {}).get("distinct_activities") or 0
    if not pairs and not a2:
        return {"scope": "none", "pairs": [], "milestones": [], "reasons": [],
                "threshold_pairs": GATE_MAX_PAIRS}
    by_uid = {t["uid"]: t for t in model["tasks"]}
    uids = {u for p in pairs for u in (p["successor_uid"], p["predecessor_uid"])}

    def critical(t):
        if not t or t.get("actual_finish"):
            return False
        sl = t.get("total_slack_minutes")
        return bool(t.get("critical")) or (sl is not None and sl <= 0)

    blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(blob.get("definitions"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    pool = [t for t in model["tasks"] if fx_mod.considered(t) and t.get("finish")
            and not t.get("actual_finish")]
    finish_chain = set()
    if pool:
        end = max(pool, key=lambda t: (t["finish"], bool(t.get("critical")),
                                       bool(t.get("milestone")), t["id"] or 0))
        finish_chain = {n["uid"] for n in fx_mod.driving_chain(
            end, by_uid, cals, blob.get("default_uid"), slot)}
    reasons = []
    if a2:
        reasons.append("total_inversion")
    if len(pairs) > GATE_MAX_PAIRS:
        reasons.append("count")
    if any(critical(by_uid.get(u)) for u in uids):
        reasons.append("critical")
    if uids & finish_chain:
        reasons.append("finish_chain")
    milestones = []
    for m in (forensics or {}).get("milestones") or []:
        if uids & {n.get("uid") for n in m.get("chain") or []}:
            milestones.append({"id": m["id"], "name": m["name"]})
    named = [{"succ_id": p["successor_id"], "succ_name": by_uid[p["successor_uid"]]["name"],
              "pred_id": p["predecessor_id"], "pred_name": by_uid[p["predecessor_uid"]]["name"]}
             for p in pairs if p["successor_uid"] in by_uid and p["predecessor_uid"] in by_uid]
    return {"scope": "absolute" if reasons else "scoped", "pairs": named[:GATE_MAX_PAIRS + 1],
            "pair_count": len(pairs), "milestones": milestones, "reasons": reasons,
            "threshold_pairs": GATE_MAX_PAIRS,
            "basis": "absolute with total inversion, more than threshold_pairs pairs, or a pair on "
                     "an unfinished critical activity or on the chain driving the project finish; "
                     "the threshold is ours"}


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
                 productivity=None, quality=None, forecast=None, forensics=None,
                 profile=None) -> dict:
    profile = profile or prof_mod.load(None)
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
    # A profile's declared fields win over discovery, and a declared field that the
    # file does not have is reported, never silently ignored.
    declared, missing_fields = prof_mod.resolve_fields(model, profile)
    if declared:
        extra_cols = []
        for role in ("discipline", "service", "section", "work_front", "regulator_code"):
            row = declared.get(role)
            if row and row["field_id"] != grp.get("field_id"):
                extra_cols.append({"key": f"cf_{row['field_id']}", "field_id": row["field_id"],
                                   "label": row.get("alias") or row.get("field_name")})
    severity = dict(SEVERITY)
    for code in profile.get("checks_optional") or []:
        if code in ("B", "F"):
            severity[code] = "high"
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
    # Zero against zero agrees about nothing: an activity with no earned value on
    # either side is set apart, never counted as a match. And a file whose own
    # earned value is zero on EVERY activity did not compute it at all, in which
    # case there is nothing to reconcile and no gap to explain.
    both_zero = file_bcwp_nonzero = file_bcws_nonzero = 0
    ahead_of_baseline = []   # executed before the baseline window; the tool credits nothing yet
    unexplained = []
    status = dt(model["project"].get("status_date"))
    # Tolerances stated against the raw file values they were measured with
    # (0.005 raw is zero, 0.01 raw is agreement), in currency units: money is
    # read in hundredths and converted at parse time. See parse_mspdi.money().
    tol_zero = mspdi.money_tolerance(0.005)
    tol_match = mspdi.money_tolerance(0.01)
    for t in lv:
        cost = bl_of(t).get("cost") or 0.0
        if cost <= 0:
            continue
        budget += cost
        mine = cost * pct_of(t) / 100.0
        earned += mine
        if t.get("bcwp") is not None and mine <= tol_zero and t["bcwp"] <= tol_zero:
            both_zero += 1
        elif t.get("bcwp") is not None:
            compared += 1
            earned_file += t["bcwp"]
            if t["bcwp"] > tol_zero:
                file_bcwp_nonzero += 1
            if abs(mine - t["bcwp"]) < tol_match:
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
            if t["bcws"] > tol_zero:
                file_bcws_nonzero += 1
    file_computed_ev = file_bcwp_nonzero > 0
    if not file_computed_ev:
        # Every difference would be "the file says zero": not a discrepancy to
        # classify, an input that is not there.
        ahead_of_baseline, unexplained, matches = [], [], 0
    ph_inputs = (phasing or {}).get("inputs") or {}
    # Planned-to-date exists if the tool computed BCWS, or the baseline cost is
    # time-phased in the file. With neither, a planned figure of zero is a missing
    # input and is reported as unavailable, not as zero.
    planned_available = file_bcws_nonzero > 0 or bool(ph_inputs.get("baseline_time_phased"))
    network = network_state(model, quality)
    gate = network_gate(model, res, forensics)

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
            "severity": severity[code], "severity_word": SW[severity[code]],
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
            "planned_pct": (round(g["planned"] / b * 100, 2) if b else 0.0) if planned_available else None,
            "earned_pct": round(g["earned"] / b * 100, 2) if b else 0.0,
            "findings": g["findings"], "finding_total": sum(g["findings"].values()),
        })
    group_rows.sort(key=lambda r: r["weight_pct"], reverse=True)

    lt = conv.get("link_types_evaluated") or {}
    links_text = L["links_evaluated"].format(list=", ".join(
        f"{i18n.link_type(lang, k)} {v}" for k, v in lt.items() if v))

    title = model["project"].get("title") or model["project"].get("name") or "Schedule"
    payload = {
        "kind": "review", "lang": lang, "labels": L, "language": detected,
        "page_title": page_title("review", title, lang),
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "title": title,
            # The file name only; `source` never carries a path.
            "file": os.path.basename(model.get("source") or ""),
            "status_date": fmt_date(model["project"].get("status_date"), lang),
            "generated": datetime.now().strftime("%d/%m/%Y %H:%M" if lang == "pt" else "%Y-%m-%d %H:%M"),
            "tasks": model["counts"]["tasks"], "leaves": len(lv),
            "budget": round(budget, 2),
            "percent_earned": round(earned / budget * 100, 2) if budget else None,
            "percent_planned_file": (round(planned_file / budget * 100, 2)
                                     if (budget and planned_available) else None),
            # What each reading below needs, and whether the file has it. A reading
            # whose input is missing is replaced by a sentence saying so.
            "inputs": {
                "network": network,
                "network_gate": gate,
                "file_earned_value": file_computed_ev,
                "file_planned_value": file_bcws_nonzero > 0,
                "baseline_time_phased": ph_inputs.get("baseline_time_phased"),
                "planned_available": planned_available,
            },
            "reconciliation": {
                "leaves_compared": compared, "matches_to_cent": matches,
                "both_zero_not_compared": both_zero,
                "file_computed_ev": file_computed_ev,
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
            "baseline_label": i18n.baseline_name(lang, slot),
            "with_physical_percent": model["counts"].get("with_physical_percent"),
            "grouping": grp["label"], "grouping_mode": grp["mode"],
            "grouping_uninformative": len(group_rows) < 2,
            "calendars_in_file": (model.get("calendars") or {}).get("count", 0),
            "ignored_pairs": conv.get("both_complete_pairs_ignored", 0),
            "links_evaluated": links_text,
        },
        "profile": {
            "organisation": profile.get("organisation") or "",
            "fields_missing": missing_fields,
            "sections_hidden": profile.get("sections_hidden") or [],
            "forced": {k: v for k, v in (("baseline_slot", profile.get("baseline_slot")),
                                         ("ev_method", profile.get("ev_method"))) if v},
        },
        "conventions": {
            **conv,
            "threshold_unit": CV["threshold_unit"], "baseline_slot_basis": CV["slot_basis"],
            "baseline_label": i18n.baseline_name(lang, slot),
            "population": CV["population"], "network_counting": CV["network_counting"],
            "working_days": CV["working_calendar"] if conv.get("calendars_from_file")
            else CV["working_fallback"],
            "percent_source": CV["percent_source"],
            "tolerance_text": i18n.fmt(CV["tolerance"], n=conv["tolerance_days"]),
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
    # The banner over the findings says what the verdict reading says, from the
    # same sentences, so the two cannot disagree on how far the breach reaches.
    gate["text"] = narrative_mod.gate_sentences(gate, lang) if gate["scope"] == "scoped" else []
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


def baseline_label(slot, L) -> str | None:
    """The baseline in the words the tool itself uses, or nothing.

    Slot 0 is simply "the baseline": naming it tells a reader nothing and reads as
    a zero. Any other slot is worth a line, because the comparison is then against
    a baseline other than the one most people assume.
    """
    if slot in (None, "", "0", 0):
        return None
    return i18n.fmt(L["baseline_n"], n=slot)


def page_title(kind: str, title: str, lang: str) -> str:
    C = i18n.cycle_text(lang)
    return C["page_title_cycle" if kind == "cycle" else "page_title_review"].format(title=title)


def _cycle_warnings(cmp_res, C, lang) -> list:
    """The comparison's warnings in the report's language, from their codes.

    A comparison produced by an older engine carries only the English sentences;
    those are shown as they are rather than dropped.
    """
    codes = cmp_res.get("warning_codes")
    if codes is None:
        return [{"text": w, "severity": "high"} for w in cmp_res.get("warnings", [])]
    out = []
    for w in codes:
        args = {k: v for k, v in w.items() if k != "code"}
        if "status_date" in w["code"]:
            args = {k: fmt_date(v, lang) for k, v in args.items()}
        if "gap" in args:
            g = narrative_mod.fnum(args["gap"], 2, lang)
            args["gap"] = g if g.startswith("-") else "+" + g
        if w["code"] == "residue_named":
            args["terms"] = "; ".join(narrative_mod.residual_parts(cmp_res, lang))
        text = C.get("w_" + w["code"])
        if text:
            out.append({"text": i18n.fmt(text, **args),
                        "severity": "critical" if w["code"] == "past_rewritten" else "high"})
    # The rewritten past leads: it is the one that invalidates what was already reported.
    out.sort(key=lambda x: x["severity"] != "critical")
    return out


def _cycle_sections(cmp_res, lang, C, readings) -> list:
    """The six readings of the model, each as one self-contained block.

    Rows are prepared here in the report's language (dates, link and constraint
    names); the untouched figures stay in the `-cycle.json` sidecar.
    """
    SW = i18n.severity_words(lang)
    QT = i18n.quality_text(lang)

    def D(v):
        return fmt_date(v, lang)

    def col(label_key, key, **flags):
        return {"label": C[label_key], "key": key, **flags}

    def yn(v):
        return C["yes"] if v else C["no"]

    def lag_text(link_type, lag):
        if link_type is None:
            return None
        s = i18n.link_type(lang, link_type)
        if lag and lag.get("value"):
            v = lag["value"]
            num = narrative_mod.fnum(abs(v), 0 if float(v).is_integer() else 2, lang)
            unit = "%" if lag.get("unit") == "percent" else " " + C["unit_d"]
            s += f" {'+' if v > 0 else '−'} {num}{unit}"
        return s

    def con_text(code, date):
        s = i18n.constraint(lang, code)
        return f"{s} {D(date)}" if date else s

    ROW = [col("col_row", "id"), col("col_activity", "name")]
    out = []

    def section(code, key, severity, badge, tiles, lists, empty):
        out.append({
            "code": code, "id": key, "title": C[key + "_title"], "subtitle": C[key + "_sub"],
            "severity": severity, "severity_word": SW[severity], "badge": badge,
            "criterion": C[key + "_criterion"], "reproduce": C[key + "_reproduce"],
            "reading": readings.get(key) or [],
            "tiles": tiles, "lists": [l for l in lists if l["rows"]], "empty": empty,
        })

    # ---- C1 project finish
    pf = cmp_res.get("project_finish")
    if pf:
        fp, fc = pf["previous"], pf["current"]
        d = pf.get("delta_days")
        drv = fc.get("driver")
        moved = d is not None and abs(d) >= 0.05
        tiles = [
            {"label": C["t_finish_before"], "value": D(fp.get("finish")), "small": True},
            {"label": C["t_finish_after"], "value": D(fc.get("finish")), "small": True,
             "sev": "al" if (moved and d > 0) else ""},
            {"label": C["t_finish_delta"], "value": d, "signed": True, "decimals": 0,
             "caption": C["t_finish_delta_cap"], "sev": "cr" if (moved and d > 0) else ""},
        ]
        if drv:
            tiles.append({"label": C["t_finish_driver"], "value": drv["name"], "text": True,
                          "caption": C["t_driver_cap_row"].format(id=drv["id"])})
        chain = [{"id": n["id"], "name": n["name"], "finish": D(n.get("finish")),
                  "critical": yn(n.get("critical")),
                  "via": i18n.link_type(lang, n["via"]) if n.get("via") else None,
                  "started": yn(n.get("started"))} for n in fc.get("chain") or []]
        section("C1", "c1", "high" if (moved and d > 0) else "view",
                None, tiles,
                [{"title": C["l_chain"], "count": len(chain), "rows": chain,
                  "columns": ROW + [col("col_finish", "finish"), col("col_critical", "critical"),
                                    col("col_via", "via"), col("col_started", "started")]}],
                empty=False)

    # ---- C2 critical path
    cp = cmp_res.get("critical_path")
    if cp:
        def cp_row(r):
            return {"id": r["id"], "name": r["name"], "fb": r["float_before_days"],
                    "fa": r["float_after_days"], "fell": r.get("float_fell_days"),
                    "finb": D(r.get("finish_before")), "fina": D(r.get("finish_after")),
                    "completed": yn(r["completed"]) if "completed" in r else None}
        floats = [col("col_float_before", "fb"), col("col_float_after", "fa")]
        dates = [col("col_finish_before", "finb"), col("col_finish_after", "fina")]
        ne, nl, nf = len(cp["entered"]), len(cp["left"]), cp["float_fell_count"]
        section("C2", "c2", "high" if ne else ("check" if (nl or nf) else "view"), ne,
                [{"label": C["t_entered"], "value": ne, "caption": C["t_entered_cap"],
                  "sev": "al" if ne else ""},
                 {"label": C["t_left"], "value": nl, "caption": C["t_left_cap"]},
                 {"label": C["t_fell"], "value": nf, "caption": C["t_fell_cap"],
                  "sev": "al" if nf else ""}],
                [{"title": C["l_entered"], "count": ne, "rows": [cp_row(r) for r in cp["entered"]],
                  "columns": ROW + floats + dates},
                 {"title": C["l_left"], "count": nl, "rows": [cp_row(r) for r in cp["left"]],
                  "columns": ROW + floats + [col("col_completed", "completed")] + dates},
                 {"title": i18n.fmt(C["l_fell"], n=len(cp["float_fell_top"]), total=nf),
                  "count": len(cp["float_fell_top"]),
                  "rows": [cp_row(r) for r in cp["float_fell_top"]],
                  "columns": ROW + floats + [col("col_float_fell", "fell")] + dates}],
                empty=not (ne or nl or nf))

    # ---- C3 logic
    lg = cmp_res.get("logic")
    if lg:
        def link_row(r):
            return {"id": r["id"], "name": r["name"], "pid": r["predecessor_id"],
                    "pname": r["predecessor_name"],
                    "before": lag_text(r["type_before"], r["lag_before"]),
                    "after": lag_text(r["type_after"], r["lag_after"])}

        def con_row(r):
            return {"id": r["id"], "name": r["name"],
                    "before": con_text(r["type_before"], r["date_before"]),
                    "after": con_text(r["type_after"], r["date_after"])}
        link_cols = ROW + [col("col_pred_row", "pid"), col("col_predecessor", "pname"),
                           col("col_link_before", "before"), col("col_link_after", "after")]
        con_cols = ROW + [col("col_constraint_before", "before"),
                          col("col_constraint_after", "after")]
        a, rm = len(lg["links_added"]), len(lg["links_removed"])
        ed = len(lg["lag_changed"]) + len(lg["type_changed"])
        cn = (len(lg["constraints_added"]) + len(lg["constraints_changed"])
              + len(lg["constraints_removed"]))
        total = a + rm + ed + cn
        lists = [{"title": C[t], "count": len(lg[k]), "rows": [fn(r) for r in lg[k]], "columns": cols}
                 for t, k, fn, cols in (
                     ("l_links_added", "links_added", link_row, link_cols),
                     ("l_links_removed", "links_removed", link_row, link_cols),
                     ("l_lag", "lag_changed", link_row, link_cols),
                     ("l_type", "type_changed", link_row, link_cols),
                     ("l_c_added", "constraints_added", con_row, con_cols),
                     ("l_c_changed", "constraints_changed", con_row, con_cols),
                     ("l_c_removed", "constraints_removed", con_row, con_cols))]
        section("C3", "c3", "check" if total else "view", total,
                [{"label": C["t_links_added"], "value": a, "caption": C["t_links_cap"]},
                 {"label": C["t_links_removed"], "value": rm, "caption": C["t_links_cap"]},
                 {"label": C["t_links_edited"], "value": ed, "caption": C["t_links_edited_cap"]},
                 {"label": C["t_constraints"], "value": cn, "caption": C["t_constraints_cap"]}],
                lists, empty=not total)

    # ---- C4 durations edited before any start
    du = cmp_res.get("duration_changed")
    if du is not None:
        rows = [{"id": r["id"], "name": r["name"], "before": r["duration_before_days"],
                 "after": r["duration_after_days"], "delta": r["delta_days"],
                 "finb": D(r.get("finish_before")), "fina": D(r.get("finish_after"))} for r in du]
        section("C4", "c4", "check" if du else "view", len(du),
                [{"label": C["t_dur"], "value": len(du), "caption": C["t_dur_cap"]},
                 {"label": C["t_dur_net"], "value": round(sum(r["delta_days"] for r in du), 1),
                  "signed": True, "decimals": 1, "caption": C["t_dur_net_cap"]}],
                [{"title": C["l_dur"], "count": len(rows), "rows": rows,
                  "columns": ROW + [col("col_dur_before", "before"), col("col_dur_after", "after"),
                                    col("col_delta_d", "delta", signed=True),
                                    col("col_finish_before", "finb"),
                                    col("col_finish_after", "fina")]}],
                empty=not du)

    # ---- C5 past rewritten
    pr = cmp_res.get("past_rewritten")
    if pr:
        def date_row(r):
            return {"id": r["id"], "name": r["name"], "before": D(r["before"]),
                    "after": D(r["after"]) if r["after"] else C["withdrawn"],
                    "moved": r["moved_days"],
                    "on_bl": C["yes"] if r.get("matches_baseline") else None}
        date_cols = ROW + [col("col_before", "before"), col("col_after", "after"),
                           col("col_moved_cal", "moved", signed=True),
                           col("col_matches_bl", "on_bl")]
        pct = [{"id": r["id"], "name": r["name"], "field": C["field_" + r["field"]],
                "before": r["before"], "after": r["after"], "delta": r["delta_points"]}
               for r in pr["percent_decreased"]]
        gone = [{"id": r["id"], "name": r["name"], "pct": r["percent"], "cost": r["baseline_cost"],
                 "ev": r["earned_erased"]} for r in pr.get("removed_with_progress") or []]
        ns, nf, np_, ng = len(pr["actual_start"]), len(pr["actual_finish"]), len(pct), len(gone)
        section("C5", "c5", "critical" if pr["activities"] else "view", pr["activities"],
                [{"label": C["t_past_start"], "value": ns, "caption": C["t_past_start_cap"],
                  "sev": "cr" if ns else ""},
                 {"label": C["t_past_finish"], "value": nf, "caption": C["t_past_finish_cap"],
                  "sev": "cr" if nf else ""},
                 {"label": C["t_past_pct"], "value": np_, "caption": C["t_past_pct_cap"],
                  "sev": "cr" if np_ else ""}]
                + ([{"label": C["t_past_gone"], "value": ng, "caption": C["t_past_gone_cap"],
                     "sev": "cr"}] if ng else []),
                [{"title": C["l_past_start"], "count": ns, "columns": date_cols,
                  "rows": [date_row(r) for r in pr["actual_start"]]},
                 {"title": C["l_past_finish"], "count": nf, "columns": date_cols,
                  "rows": [date_row(r) for r in pr["actual_finish"]]},
                 {"title": C["l_past_pct"], "count": np_, "rows": pct,
                  "columns": ROW + [col("col_field", "field"), col("col_before", "before"),
                                    col("col_after", "after"),
                                    col("col_delta_pp", "delta", signed=True)]},
                 {"title": C["l_past_gone"], "count": ng, "rows": gone,
                  "columns": [col("col_row_prev", "id"), col("col_activity", "name"),
                              col("col_pct_prev", "pct"), col("col_bl_cost", "cost", decimals=2),
                              col("col_ev_erased", "ev", decimals=2)]}],
                empty=not pr["activities"])

    # ---- C6 network quality, side by side
    q = cmp_res.get("quality")
    if q:
        status = {"pass": C["q_pass"], "fail": C["q_fail"], None: ""}
        change = {"improved": C["chg_improved"], "worsened": C["chg_worsened"],
                  "unchanged": C["chg_unchanged"], None: C["chg_na"]}
        rows = []
        for m in q["metrics"]:
            p, c = m["previous"], m["current"]
            rows.append({
                "code": m["code"], "metric": QT.get(m["code"], (m["code"], ""))[0],
                "cb": p["count"] if p["population"] else None,
                "ca": c["count"] if c["population"] else None,
                "sb": p["share_pct"], "sa": c["share_pct"], "sd": m["share_delta_points"],
                "stb": status.get(p["status"], ""), "sta": status.get(c["status"], ""),
                "change": change.get(m["change"], ""),
                "_tone": {"worsened": "bad", "improved": "good"}.get(m["change"]),
            })
        worse = sum(1 for m in q["metrics"] if m["change"] == "worsened")
        better = sum(1 for m in q["metrics"] if m["change"] == "improved")
        crossed = sum(1 for m in q["metrics"] if m.get("crossed") == "pass->fail")
        section("C6", "c6", "high" if crossed else ("check" if worse else "view"), None,
                [{"label": C["t_q_worse"], "value": worse, "caption": C["t_q_cap"],
                  "sev": "al" if worse else ""},
                 {"label": C["t_q_better"], "value": better, "caption": C["t_q_cap"],
                  "sev": "vs" if better else ""},
                 {"label": C["t_q_crossed"], "value": crossed, "caption": C["t_q_cap"],
                  "sev": "cr" if crossed else ""}],
                [{"title": C["l_quality"], "count": len(rows), "rows": rows, "open": True,
                  "columns": [{"label": "", "key": "code"}, col("col_metric", "metric"),
                              col("col_count_before", "cb"), col("col_count_after", "ca"),
                              col("col_share_before", "sb", pct=True),
                              col("col_share_after", "sa", pct=True),
                              col("col_share_delta", "sd", signed=True),
                              col("col_status_before", "stb"), col("col_status_after", "sta"),
                              col("col_change", "change", tone=True)]}],
                empty=False)
    return out


def build_cycle(cmp_res, theme=None, lang=None, detected=None) -> dict:
    lang = lang or (detected or {}).get("lang") or "en"
    C = {**i18n.ui(lang), **i18n.cycle_text(lang)}
    QT = i18n.quality_text(lang)
    prev, curr = cmp_res["previous"], cmp_res["current"]
    readings = narrative_mod.build_cycle(
        cmp_res, lang, fmt_date, metric_title=lambda code: QT.get(code, (code, ""))[0])
    title = curr.get("title") or prev.get("title") or C["cycle_title"]
    conv = cmp_res.get("conventions") or {}
    conventions = [
        {"label": C["cv_" + k],
         "text": i18n.conventions(lang)["denominator"] if k == "denominator" else C["cvt_" + k]}
        for k in ("matching", "population", "logic_population", "denominator", "aggregates",
                  "critical", "links", "finish_delta", "float_and_duration")
        if k in conv
    ]
    finish = (cmp_res.get("project_finish") or {}).get("current") or {}
    return {
        "kind": "cycle", "lang": lang, "labels": C,
        "page_title": page_title("cycle", title, lang),
        "language": detected or {"lang": lang, "confidence": "inherited"},
        "theme": {**DEFAULT_THEME, **(theme or {})},
        "meta": {
            "generated": datetime.now().strftime("%d/%m/%Y %H:%M" if lang == "pt" else "%Y-%m-%d %H:%M"),
            "title": title,
            # File names only. A path is somebody's folder structure.
            "previous_file": prev.get("source"), "current_file": curr.get("source"),
            "previous_status_date": fmt_date(prev.get("status_date"), lang),
            "current_status_date": fmt_date(curr.get("status_date"), lang),
            "current_finish": fmt_date(finish.get("finish"), lang),
            "baseline_label": baseline_label(curr.get("baseline_slot"), C),
            "budget": curr.get("budget_at_completion"),
            "previous_percent_earned": prev.get("percent_earned"),
            "current_percent_earned": curr.get("percent_earned"),
            "movement_points": cmp_res.get("movement_points"),
            "explained_points": cmp_res.get("decomposition_sums_to_points"),
            "unexplained_points": cmp_res.get("movement_unexplained_points"),
        },
        "conventions": {**conv, "denominator": i18n.conventions(lang)["denominator"]},
        "conventions_list": conventions,
        "warnings": _cycle_warnings(cmp_res, C, lang),
        "readings": readings,
        "sections": _cycle_sections(cmp_res, lang, C, readings),
        "trend": {
            "execution": [t for t in cmp_res["trend"] if t["reading"] == "execution"],
            "replan": [t for t in cmp_res["trend"] if t["reading"] == "replan"],
            "reference": cmp_res["baseline_moved"],
            "words": {"execution": C["card_execution"].lower(), "replan": C["card_replan"].lower()},
        },
        "decomposition": cmp_res["decomposition"],
        "unmatched": cmp_res["unmatched"],
    }
