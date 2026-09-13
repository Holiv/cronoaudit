#!/usr/bin/env python3
"""The S-curve from the file's own time-phased data, reconciled against its totals.

    python3 phasing.py schedule.xml -o phasing.json [--group-field <field id>]

Nothing here invents a distribution. Project writes, per task, its baseline cost
by period and its physical percent by day. Measured on a 6,484-task export:

* the per-task sum of the baseline-cost blocks equals the baseline cost on
  4,677 of 4,677 tasks that carry one;
* the same sum up to the status date equals the BCWS the file writes on
  5,249 of 5,251 tasks.

So the planned curve is the file's, not a guess -- and when the file already
carries the result of the expensive calculation, derive from it.

Two things worth knowing about the physical-percent blocks. They are Project's
own spread of the current physical percent across the actual duration to date,
not a record of when each update was reported, so the earned curve's shape is
the tool's interpolation -- the same shape the tool draws in its own graphs. And
a non-working day carries the value 32768, a sentinel, not a percent.

The alternative method's curve is included as sensitivity: the file declares one
earned-value method, and the report shows what the other would say, because on
a real programme the two differed by 1.88 points of progress.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta

NS = "{http://schemas.microsoft.com/project}"
SENTINEL = 32768.0  # what Project writes on a non-working day in a percent block
TYPE_BASELINE_COST = "10"
TYPE_PHYSICAL_PCT = "11"


def month_key(d: datetime) -> str:
    return d.strftime("%Y-%m")


def stream(path: str, group_field: str | None):
    """Yield one compact record per leaf task, reading the file once."""
    status = None
    ev_method = None
    floor = None
    for ev, el in ET.iterparse(path, events=("end",)):
        tag = el.tag.replace(NS, "")
        if tag == "StatusDate" and status is None and el.text:
            status = datetime.fromisoformat(el.text)
            continue
        if tag == "StartDate" and floor is None and el.text:
            # Project writes its "no date" epoch (1984) into some blocks. Anything
            # phased more than a year before the project starts is that epoch, not a
            # plan, and one such block opens a phantom period at the head of the curve.
            floor = (datetime.fromisoformat(el.text) - timedelta(days=366)).date().isoformat()
            continue
        if tag == "DefaultTaskEVMethod" and ev_method is None:
            ev_method = int(el.text or 0)
            continue
        if tag != "Task":
            continue
        if el.findtext(NS + "Summary") != "0" or el.findtext(NS + "Active") == "0" \
                or el.findtext(NS + "ExternalTask") == "1":
            el.clear()
            continue
        bl = el.find(NS + "Baseline")
        rec = {
            "id": int(el.findtext(NS + "ID") or 0),
            "uid": int(el.findtext(NS + "UID") or 0),
            "cost": float(bl.findtext(NS + "Cost") or 0) if bl is not None else 0.0,
            "bcws": float(el.findtext(NS + "BCWS") or 0),
            "bcwp": float(el.findtext(NS + "BCWP") or 0),
            "physical": float(el.findtext(NS + "PhysicalPercentComplete") or 0),
            "percent": float(el.findtext(NS + "PercentComplete") or 0),
            "actual_start": el.findtext(NS + "ActualStart"),
            "actual_finish": el.findtext(NS + "ActualFinish"),
            "ev_method": int(el.findtext(NS + "EarnedValueMethod") or (ev_method or 0)),
            "group": None,
            "planned_by_day": defaultdict(float),
            "physical_by_day": defaultdict(float),
        }
        if group_field:
            for ea in el.findall(NS + "ExtendedAttribute"):
                if ea.findtext(NS + "FieldID") == group_field:
                    rec["group"] = ea.findtext(NS + "Value")
                    break
        for tp in el.findall(NS + "TimephasedData"):
            ty = tp.findtext(NS + "Type")
            if ty not in (TYPE_BASELINE_COST, TYPE_PHYSICAL_PCT):
                continue
            raw = (tp.findtext(NS + "Value") or "").strip()
            if not raw:
                # A block with no value is a block with nothing in it. Real files
                # carry these; a fixture never did until one broke the run.
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if ty == TYPE_PHYSICAL_PCT and value >= SENTINEL:
                continue
            day = (tp.findtext(NS + "Start") or "")[:10]
            if not day or day < "1990-01-01" or (floor and day < floor):
                rec["dropped_epoch"] = rec.get("dropped_epoch", 0) + 1
                continue
            if ty == TYPE_BASELINE_COST:
                rec["planned_by_day"][day] += value
            else:
                rec["physical_by_day"][day] += value
        el.clear()
        yield status, rec


def spread_evenly(cost: float, pct: float, start: str | None, end: str | None):
    """The duration-method earned value, spread across the actual span.

    Derived, not read: the file phases physical percent, not duration percent.
    Marked `inferred` in the output for that reason.
    """
    if not start or cost <= 0 or pct <= 0:
        return {}
    a = datetime.fromisoformat(start)
    b = datetime.fromisoformat(end) if end else None
    if b is None or b < a:
        b = a
    days = (b.date() - a.date()).days + 1
    per_day = cost * pct / 100.0 / days
    out = {}
    cur = a.date()
    for _ in range(days):
        out[cur.isoformat()] = per_day
        cur += timedelta(days=1)
    return out


def build(path: str, group_field: str | None) -> dict:
    status = None
    tasks = 0
    with_cost = 0
    sum_eq_cost = 0
    upto_eq_bcws = 0
    earned_eq_bcwp = 0
    bac = 0.0
    dropped = 0
    method_votes = defaultdict(int)

    planned = defaultdict(float)      # day -> planned cost
    earned = defaultdict(float)       # day -> earned cost (physical method, file's spread)
    earned_alt = defaultdict(float)   # day -> earned cost (duration method, derived)
    by_group = defaultdict(lambda: {"planned": defaultdict(float), "earned": defaultdict(float),
                                    "bac": 0.0})

    for st, rec in stream(path, group_field):
        status = status or st
        tasks += 1
        method_votes[rec["ev_method"]] += 1
        cost = rec["cost"]
        if cost > 0:
            with_cost += 1
            bac += cost
        s10 = sum(rec["planned_by_day"].values())
        if cost > 0 and abs(s10 - cost) < 0.5:
            sum_eq_cost += 1
        cutoff = status.date().isoformat() if status else "9999-12-31"
        s10_upto = sum(v for d, v in rec["planned_by_day"].items() if d <= cutoff)
        if abs(s10_upto - rec["bcws"]) < 0.5:
            upto_eq_bcws += 1

        for d, v in rec["planned_by_day"].items():
            planned[d] += v
        g = by_group[rec["group"] or "(unassigned)"] if group_field else None
        if g is not None:
            g["bac"] += cost
            for d, v in rec["planned_by_day"].items():
                g["planned"][d] += v

        if cost > 0 and abs(cost * rec["physical"] / 100.0 - rec["bcwp"]) < 0.01:
            earned_eq_bcwp += 1
        dropped += rec.get("dropped_epoch", 0)

        # Earned, physical method: the file's daily spread of the percent, times cost.
        phys_total = sum(rec["physical_by_day"].values())
        if cost > 0 and phys_total > 0:
            # Normalise to the task's own physical percent so rounding in the daily
            # blocks cannot drift the total away from cost x physical.
            scale = (rec["physical"] / phys_total) if phys_total else 0.0
            for d, v in rec["physical_by_day"].items():
                e = cost * (v * scale) / 100.0
                earned[d] += e
                if g is not None:
                    g["earned"][d] += e
        elif cost > 0 and rec["physical"] > 0:
            # Percent set but no daily blocks: land it on the actual start day.
            day = (rec["actual_start"] or cutoff)[:10]
            e = cost * rec["physical"] / 100.0
            earned[day] += e
            if g is not None:
                g["earned"][day] += e

        # Earned, duration method: derived spread of cost x percent complete.
        end = rec["actual_finish"] or (status.isoformat() if status else None)
        for d, v in spread_evenly(cost, rec["percent"], rec["actual_start"], end).items():
            earned_alt[d] += v

    # ---- monthly series with cumulatives
    months = sorted(set(month_key(datetime.fromisoformat(d)) for d in
                        list(planned) + list(earned) + list(earned_alt)))
    status_month = month_key(status) if status else None
    p_cum = e_cum = a_cum = 0.0
    periods = []
    for mth in months:
        p = sum(v for d, v in planned.items() if d.startswith(mth))
        e = sum(v for d, v in earned.items() if d.startswith(mth))
        a = sum(v for d, v in earned_alt.items() if d.startswith(mth))
        p_cum += p
        e_cum += e
        a_cum += a
        past = status_month is None or mth <= status_month
        periods.append({
            "period": mth, "planned": round(p, 2), "earned": round(e, 2) if past else None,
            "earned_alt": round(a, 2) if past else None,
            "planned_cum": round(p_cum, 2),
            "earned_cum": round(e_cum, 2) if past else None,
            "earned_alt_cum": round(a_cum, 2) if past else None,
            "sv_cum": round(e_cum - p_cum, 2) if past else None,
            "spi_cum": round(e_cum / p_cum, 4) if past and p_cum > 0 else None,
            "planned_cum_pct": round(p_cum / bac * 100, 2) if bac else None,
            "earned_cum_pct": round(e_cum / bac * 100, 2) if (past and bac) else None,
            "earned_alt_cum_pct": round(a_cum / bac * 100, 2) if (past and bac) else None,
        })

    cutoff = status.date().isoformat() if status else "9999-12-31"
    planned_to_date = sum(v for d, v in planned.items() if d <= cutoff)
    earned_to_date = sum(v for d, v in earned.items() if d <= cutoff)
    alt_to_date = sum(v for d, v in earned_alt.items() if d <= cutoff)
    # The tool can spread a physical percent past the status date. That value is
    # real progress, credited on a day the curve has not reached; it explains the
    # gap between earned-to-date here and cost x physical summed flat, and it is
    # reported rather than absorbed.
    earned_after_status = sum(v for d, v in earned.items() if d > cutoff)

    groups_out = {}
    for name, g in by_group.items():
        gp = ge = 0.0
        rows = []
        for mth in months:
            gp += sum(v for d, v in g["planned"].items() if d.startswith(mth))
            ge += sum(v for d, v in g["earned"].items() if d.startswith(mth))
            past = status_month is None or mth <= status_month
            rows.append({"period": mth,
                         "planned_cum_pct": round(gp / g["bac"] * 100, 2) if g["bac"] else None,
                         "earned_cum_pct": round(ge / g["bac"] * 100, 2) if (past and g["bac"]) else None})
        groups_out[name] = {"bac": round(g["bac"], 2), "periods": rows}

    declared = max(method_votes, key=method_votes.get) if method_votes else 1
    return {
        "source": path,
        "status_date": status.isoformat() if status else None,
        "granularity": "month",
        "method": "physical" if declared == 1 else "percent",
        "method_mixed": len(method_votes) > 1,
        "bac": round(bac, 2),
        "totals": {
            "planned_to_date": round(planned_to_date, 2),
            "earned_to_date": round(earned_to_date, 2),
            "earned_alt_to_date": round(alt_to_date, 2),
            "earned_phased_after_status": round(earned_after_status, 2),
            "planned_pct": round(planned_to_date / bac * 100, 2) if bac else None,
            "earned_pct": round(earned_to_date / bac * 100, 2) if bac else None,
            "earned_alt_pct": round(alt_to_date / bac * 100, 2) if bac else None,
            "sv": round(earned_to_date - planned_to_date, 2),
            "spi": round(earned_to_date / planned_to_date, 4) if planned_to_date else None,
            "method_gap_points": round((earned_to_date - alt_to_date) / bac * 100, 2) if bac else None,
        },
        "reconciliation": {
            "tasks": tasks, "with_cost": with_cost,
            "phasing_sum_equals_cost": sum_eq_cost,
            "phasing_to_status_equals_bcws": upto_eq_bcws,
            "earned_equals_bcwp": earned_eq_bcwp,
            "epoch_blocks_dropped": dropped,
        },
        "provenance": {
            "planned": "measured: the file's own baseline-cost blocks, type 10",
            "earned": "measured: the file's own daily physical-percent blocks, type 11, times "
                      "baseline cost; shape is the tool's spread, not the reporting dates",
            "earned_alt": "inferred: cost times duration percent, spread evenly over the actual "
                          "span; the file does not phase this method",
        },
        "periods": periods,
        "by_group": groups_out,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("xml")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--group-field", help="stable field id to build per-group curves")
    args = ap.parse_args()
    res = build(args.xml, args.group_field)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    r = res["reconciliation"]
    print(f"{args.xml}: {r['tasks']} tasks, phasing = cost on {r['phasing_sum_equals_cost']}, "
          f"to-status = BCWS on {r['phasing_to_status_equals_bcws']} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
