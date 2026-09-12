#!/usr/bin/env python3
"""Looking forward from the schedule: when it really finishes, what the next weeks
demand, where the practised rate does not reach the required one, and how much of
what remains sits in the rainy season.

    python3 forecast.py model.json scurve.json productivity.json -o forecast.json

Five outputs, each from data the file already carries:

* **Earned Schedule** (Lipke, 2003). Classic earned-value schedule measures are in
  money and converge to "on plan" as the project ends, however late it is. Earned
  Schedule asks instead: on what date did the planned curve reach the value earned
  today? That date is ES. From it: SV(t) = ES − AT in time, SPI(t) = ES / AT, an
  independent duration at completion IEAC(t) = PD / SPI(t), and TSPI, the
  efficiency the remainder would need to finish on the planned date. It is an
  aggregate, cost-weighted view: it does not see the critical path, so it is set
  beside the schedule's own finish, never in its place. The gap is the conversation.
* **Look-ahead**: what must start and finish in the next four and eight weeks, by
  group, weighted by baseline cost, and whether the planned earning of the window
  is reachable at the practised rate.
* **Rates by group**: practised earning per week against the earning per week the
  remainder needs to land on the group's baseline finish.
* **Milestone bands**: the empirical distribution of finish slippage observed in this
  snapshot applied to future milestones as P50 and P80. Not a simulation with an
  invented premise; a series of snapshots would replace it with observed cycles.
* **Rainy-season exposure**: how much of the remaining cost, spread over each
  activity's current span, falls in months where that activity's calendar carries
  a productivity reserve — and how much more moves into it if everything slips a
  month.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import calendars as cal_mod

RESERVE_DAYS_PER_MONTH = 4   # a month with this many non-working exceptions is a reserve month


def dt(v):
    return datetime.fromisoformat(v) if v else None


def fmt(d):
    return d.strftime("%Y-%m-%d") if d else None


def month_end(period: str) -> datetime:
    y, m = int(period[:4]), int(period[5:7])
    nxt = datetime(y + (m // 12), (m % 12) + 1, 1)
    return nxt - timedelta(days=1)


def month_start(period: str) -> datetime:
    return datetime(int(period[:4]), int(period[5:7]), 1)


def considered(t):
    return not t.get("summary") and t.get("active") is not False and not t.get("external")


# ---------------------------------------------------------------------------
# Earned Schedule
# ---------------------------------------------------------------------------
def earned_schedule(scurve: dict, model: dict) -> dict:
    periods = scurve.get("periods") or []
    status = dt(scurve.get("status_date"))
    bac = scurve.get("bac") or 0.0
    ev_pct = (scurve.get("totals") or {}).get("earned_pct")
    pv_pct = (scurve.get("totals") or {}).get("planned_pct")
    if not periods or status is None or ev_pct is None or not bac:
        return {"available": False, "reason": "no phased curve or no status date"}

    # Cumulative planned percent at each month end, from the first month that plans
    # anything. Interpolate linearly inside a month to find the date PV reached EV.
    pts = [(month_end(p["period"]), p["planned_cum_pct"] or 0.0) for p in periods]
    first = next((month_start(p["period"]) for p in periods if (p["planned"] or 0) > 0), None)
    if first is None:
        return {"available": False, "reason": "nothing planned"}
    pts = [(first, 0.0)] + [pt for pt in pts if pt[0] >= first]

    es_date = None
    for (d0, v0), (d1, v1) in zip(pts, pts[1:]):
        if v1 >= ev_pct > v0 or (ev_pct == v0 == 0):
            frac = 0.0 if v1 == v0 else (ev_pct - v0) / (v1 - v0)
            es_date = d0 + timedelta(days=(d1 - d0).days * frac)
            break
    if es_date is None:
        es_date = pts[-1][0] if ev_pct >= pts[-1][1] else first

    # Planned duration: from the first planned day to the last baseline finish.
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    bl_finishes = [dt(((t.get("baselines") or {}).get(slot) or {}).get("finish"))
                   for t in model["tasks"] if considered(t)]
    bl_finishes = [d for d in bl_finishes if d]
    planned_finish = max(bl_finishes) if bl_finishes else None
    schedule_finish = dt(model["project"].get("finish"))

    at = (status - first).days
    es = (es_date - first).days
    pd = (planned_finish - first).days if planned_finish else None
    spi_t = round(es / at, 4) if at > 0 else None
    sv_t = es - at
    ieac_days = round(pd / spi_t) if (pd and spi_t) else None
    ieac_date = first + timedelta(days=ieac_days) if ieac_days else None
    tspi = round((pd - es) / (pd - at), 3) if (pd and pd > at) else None
    return {
        "available": True,
        "project_start": fmt(first), "status_date": fmt(status),
        "ev_pct": ev_pct, "pv_pct": pv_pct,
        "es_date": fmt(es_date), "at_days": at, "es_days": round(es, 1),
        "sv_t_days": round(sv_t, 1), "spi_t": spi_t,
        "planned_finish": fmt(planned_finish), "pd_days": pd,
        "ieac_t_days": ieac_days, "ieac_t_date": fmt(ieac_date),
        "schedule_finish": fmt(schedule_finish),
        "gap_vs_schedule_days": (ieac_date - schedule_finish).days if (ieac_date and schedule_finish) else None,
        "tspi": tspi,
        "tspi_verdict": (None if tspi is None else
                         ("recoverable" if tspi <= 1.0 else
                          ("hard" if tspi <= 1.10 else "unrecoverable"))),
        "limits": "aggregate and cost-weighted; blind to the critical path; inherits the "
                  "baseline slot, the earned-value method and everything the planned curve "
                  "inherits. Set beside the schedule's own finish, never in its place.",
    }


# ---------------------------------------------------------------------------
# Look-ahead
# ---------------------------------------------------------------------------
def lookahead(model: dict, scurve: dict, group_field: str | None, weeks_list=(4, 8)) -> list:
    status = dt(model["project"].get("status_date"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    if status is None:
        return []
    leaves = [t for t in model["tasks"] if considered(t)]
    bac = scurve.get("bac") or sum(((t.get("baselines") or {}).get(slot) or {}).get("cost") or 0
                                   for t in leaves) or 1.0

    def group_of(t):
        if group_field:
            return (t.get("custom") or {}).get(group_field) or "(unassigned)"
        return (t.get("outline_number") or "").split(".")[0] or "(unassigned)"

    # Practised earning per week, project level, from the last 8 weeks of the curve.
    periods = scurve.get("periods") or []
    past = [p for p in periods if p.get("earned") is not None]
    recent = past[-2:] if len(past) >= 2 else past
    weeks_recent = sum((month_end(p["period"]) - month_start(p["period"])).days + 1 for p in recent) / 7.0
    practised_per_week = (sum(p["earned"] or 0 for p in recent) / weeks_recent) if weeks_recent else 0.0

    out = []
    for w in weeks_list:
        end = status + timedelta(weeks=w)
        starts, finishes = [], []
        by_group = defaultdict(lambda: {"starts": 0, "finishes": 0, "cost": 0.0})
        planned_in_window = 0.0
        for t in leaves:
            cost = ((t.get("baselines") or {}).get(slot) or {}).get("cost") or 0.0
            s, f = dt(t.get("start")), dt(t.get("finish"))
            g = group_of(t)
            if s and status < s <= end and not t.get("actual_start"):
                starts.append({"id": t["id"], "name": t["name"], "group": g,
                               "start": fmt(s), "cost": round(cost, 2),
                               "weight_pct": round(cost / bac * 100, 3)})
                by_group[g]["starts"] += 1
                by_group[g]["cost"] += cost
            if f and status < f <= end and not t.get("actual_finish"):
                finishes.append({"id": t["id"], "name": t["name"], "group": g,
                                 "finish": fmt(f), "cost": round(cost, 2),
                                 "weight_pct": round(cost / bac * 100, 3)})
                by_group[g]["finishes"] += 1
            # Planned earning inside the window: the file's phasing, pro-rata by month.
        for p in periods:
            ms, me = month_start(p["period"]), month_end(p["period"])
            lo, hi = max(ms, status + timedelta(days=1)), min(me, end)
            if hi >= lo and (p.get("planned") or 0) > 0:
                planned_in_window += (p["planned"] or 0) * ((hi - lo).days + 1) / ((me - ms).days + 1)
        starts.sort(key=lambda x: -x["cost"])
        finishes.sort(key=lambda x: -x["cost"])
        projected = practised_per_week * w
        out.append({
            "weeks": w, "from": fmt(status + timedelta(days=1)), "to": fmt(end),
            "must_start": len(starts), "must_finish": len(finishes),
            "planned_earning": round(planned_in_window, 2),
            "planned_earning_pct": round(planned_in_window / bac * 100, 2),
            "projected_earning_at_practised_rate": round(projected, 2),
            "projected_pct": round(projected / bac * 100, 2),
            "reachable": bool(projected >= planned_in_window) if planned_in_window else None,
            "by_group": sorted(
                [{"group": g, **v, "cost": round(v["cost"], 2),
                  "weight_pct": round(v["cost"] / bac * 100, 2)} for g, v in by_group.items()],
                key=lambda r: -r["cost"]),
            "starts": starts[:60], "finishes": finishes[:60],
        })
    return out


# ---------------------------------------------------------------------------
# Rates by group
# ---------------------------------------------------------------------------
def rates_by_group(model: dict, scurve: dict, group_field: str | None) -> list:
    status = dt(model["project"].get("status_date"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    groups = scurve.get("by_group") or {}
    if not groups or status is None:
        return []
    # Baseline finish per group, from the model.
    last_bl = defaultdict(lambda: None)
    for t in model["tasks"]:
        if not considered(t):
            continue
        g = ((t.get("custom") or {}).get(group_field) or "(unassigned)") if group_field \
            else ((t.get("outline_number") or "").split(".")[0] or "(unassigned)")
        bf = dt(((t.get("baselines") or {}).get(slot) or {}).get("finish"))
        if bf and (last_bl[g] is None or bf > last_bl[g]):
            last_bl[g] = bf
    out = []
    for name, g in groups.items():
        rows = g.get("periods") or []
        past = [r for r in rows if r.get("earned_cum_pct") is not None]
        if not past:
            continue
        earned = past[-1]["earned_cum_pct"] or 0.0
        planned = past[-1]["planned_cum_pct"] or 0.0
        first_earn = next((r for r in past if (r.get("earned_cum_pct") or 0) > 0), None)
        weeks_elapsed = ((status - month_start(first_earn["period"])).days / 7.0) if first_earn else 0.0
        practised = earned / weeks_elapsed if weeks_elapsed > 0 else None
        bf = last_bl.get(name)
        weeks_left = ((bf - status).days / 7.0) if (bf and bf > status) else None
        required = ((100.0 - earned) / weeks_left) if weeks_left else None
        ratio = round(required / practised, 2) if (required and practised) else None
        out.append({
            "group": name, "bac": g.get("bac"), "earned_pct": earned, "planned_pct": planned,
            "practised_pct_per_week": round(practised, 3) if practised else None,
            "required_pct_per_week": round(required, 3) if required else None,
            "baseline_finish": fmt(bf), "weeks_left": round(weeks_left, 1) if weeks_left else None,
            "ratio_required_over_practised": ratio,
            "verdict": (None if ratio is None else
                        ("on pace" if ratio <= 1.0 else ("stretch" if ratio <= 1.5 else "out of reach"))),
        })
    out.sort(key=lambda r: -(r["bac"] or 0))
    return out


# ---------------------------------------------------------------------------
# Milestone bands
# ---------------------------------------------------------------------------
def milestone_bands(model: dict) -> dict:
    status = dt(model["project"].get("status_date"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    if status is None:
        return {"milestones": [], "basis": "no status date"}
    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal = cal_blob.get("default_uid")
    slips = []
    for t in model["tasks"]:
        if not considered(t) or t.get("milestone"):
            continue
        bf, f = dt(((t.get("baselines") or {}).get(slot) or {}).get("finish")), dt(t.get("finish"))
        if bf and f and (t.get("actual_start") or bf <= status):
            slips.append((f - bf).days)
    slips.sort()

    def pct(q):
        if not slips:
            return 0
        i = min(len(slips) - 1, max(0, int(round(q * (len(slips) - 1)))))
        return slips[i]

    p50, p80 = max(0, pct(0.5)), max(0, pct(0.8))
    ms = []
    for t in model["tasks"]:
        if not considered(t) or not t.get("milestone") or t.get("actual_finish"):
            continue
        f = dt(t.get("finish"))
        bf = dt(((t.get("baselines") or {}).get(slot) or {}).get("finish"))
        if f is None or f <= status:
            continue
        ms.append({
            "id": t["id"], "name": t["name"], "finish": fmt(f), "baseline_finish": fmt(bf),
            "slip_now_days": (f - bf).days if bf else None,
            "p50": fmt(f + timedelta(days=p50)), "p80": fmt(f + timedelta(days=p80)),
            "deadline": t.get("deadline"), "critical": bool(t.get("critical")),
        })
    ms.sort(key=lambda m: m["finish"])
    return {
        "sample": len(slips), "p50_days": p50, "p80_days": p80,
        "basis": "empirical: distribution of finish slippage (current minus baseline, calendar "
                 "days) across started or due activities in this snapshot, applied to each "
                 "future milestone's current finish. A series of snapshots replaces it with "
                 "observed cycle-to-cycle movement.",
        "milestones": ms[:80],
    }


# ---------------------------------------------------------------------------
# Rainy-season exposure
# ---------------------------------------------------------------------------
def rain_exposure(model: dict) -> dict:
    status = dt(model["project"].get("status_date"))
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal = cal_blob.get("default_uid")
    if status is None or not cals:
        return {"available": False}

    # Reserve months per calendar: months with at least N non-working exceptions.
    reserve = {}
    for uid, cal in cals.items():
        per_month = defaultdict(int)
        for day, ivs in cal.exception_intervals.items():
            if not ivs:
                per_month[day.strftime("%Y-%m")] += 1
        reserve[uid] = {m for m, n in per_month.items() if n >= RESERVE_DAYS_PER_MONTH}

    def spread(t, shift_days=0):
        cost = ((t.get("baselines") or {}).get(slot) or {}).get("cost") or 0.0
        phys = t.get("physical_percent_complete") or 0.0
        remaining = cost * (1 - phys / 100.0)
        s, f = dt(t.get("start")), dt(t.get("finish"))
        if remaining <= 0 or s is None or f is None:
            return {}
        s = max(s, status) + timedelta(days=shift_days)
        f = f + timedelta(days=shift_days)
        if f < s:
            f = s
        days = (f.date() - s.date()).days + 1
        per_day = remaining / days
        out = defaultdict(float)
        cur = s.date()
        for _ in range(days):
            out[cur.strftime("%Y-%m")] += per_day
            cur += timedelta(days=1)
        return out

    total = 0.0
    in_reserve = 0.0
    in_reserve_shifted = 0.0
    months = defaultdict(lambda: {"remaining": 0.0, "in_reserve": 0.0})
    for t in model["tasks"]:
        if not considered(t) or t.get("actual_finish"):
            continue
        cal_uid = t.get("calendar_uid") if t.get("calendar_uid") in cals else default_cal
        rmonths = reserve.get(cal_uid, set())
        for m, v in spread(t).items():
            total += v
            months[m]["remaining"] += v
            if m in rmonths:
                in_reserve += v
                months[m]["in_reserve"] += v
        for m, v in spread(t, 30).items():
            if m in rmonths:
                in_reserve_shifted += v
    series = [{"period": m, "remaining": round(v["remaining"], 2),
               "in_reserve": round(v["in_reserve"], 2),
               "share_in_reserve": round(v["in_reserve"] / v["remaining"] * 100, 1) if v["remaining"] else 0.0}
              for m, v in sorted(months.items())]
    return {
        "available": True,
        "reserve_rule": f"a month with at least {RESERVE_DAYS_PER_MONTH} non-working exceptions on the activity's calendar",
        "remaining_total": round(total, 2),
        "in_reserve": round(in_reserve, 2),
        "share_in_reserve_pct": round(in_reserve / total * 100, 2) if total else None,
        "share_if_slips_30_days_pct": round(in_reserve_shifted / total * 100, 2) if total else None,
        "basis": "inferred: remaining cost spread evenly over each activity's current span from "
                 "the status date; reserve months read from each activity's own calendar",
        "months": series[:60],
    }


def build(model: dict, scurve: dict, productivity: dict | None, group_field: str | None) -> dict:
    return {
        "status_date": model["project"].get("status_date"),
        "earned_schedule": earned_schedule(scurve, model),
        "lookahead": lookahead(model, scurve, group_field),
        "rates_by_group": rates_by_group(model, scurve, group_field),
        "milestone_bands": milestone_bands(model),
        "rain_exposure": rain_exposure(model),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model")
    ap.add_argument("scurve")
    ap.add_argument("productivity", nargs="?")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--group-field")
    args = ap.parse_args()
    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    with open(args.scurve, encoding="utf-8") as fh:
        scurve = json.load(fh)
    prod = None
    if args.productivity:
        with open(args.productivity, encoding="utf-8") as fh:
            prod = json.load(fh)
    res = build(model, scurve, prod, args.group_field)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    es = res["earned_schedule"]
    print(f"ES {es.get('es_date')} SPI(t) {es.get('spi_t')} IEAC(t) {es.get('ieac_t_date')} "
          f"TSPI {es.get('tspi')} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
