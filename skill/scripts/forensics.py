#!/usr/bin/env python3
"""Where did the delay come from, by which path, and when did it start?

    python3 forensics.py model.json findings.json -o forensics.json [--previous prev_model.json --cycle cycle.json]

Not a contractual delay claim: those need contemporaneous records and a formal
method. This reconstructs the mechanism, with reproducible evidence, to sustain
the meeting and the notification.

Four readings from one snapshot:

* **Driving path per milestone.** From each future milestone, walk back through
  the predecessor that actually drives each start -- the one whose finish plus lag
  lands latest -- until the chain reaches an activity that has started or an open
  end. Then find where along that chain the finish variance first appears: the
  delay's origin has a name, not an aggregate.
* **Calendar forensics.** A productivity reserve registered for one year while the
  activities on that calendar execute in another embeds optimism nothing in the
  file announces. Per calendar: exceptions per year against activity-days per year.
* **Execution pattern.** Out-of-sequence execution by month, and the distribution
  of start slippage against the baseline.
* **Two more with a previous snapshot.** Float consumed per activity and per group,
  the activities that became critical this cycle, and the movement of each
  milestone attributed to what moved on its driving chain: execution, replan or a
  moved reference.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime

import calendars as cal_mod

CHAIN_LIMIT = 60
ORIGIN_MIN_DAYS = 5


def dt(v):
    return datetime.fromisoformat(v) if v else None


def fmt(d):
    return d.strftime("%Y-%m-%d") if d else None


def considered(t):
    return not t.get("summary") and t.get("active") is not False and not t.get("external")


def link_target(pred, link):
    """The instant a link makes available for the successor, before lag."""
    kind = link["type"]
    if kind in ("FS", "FF"):
        return dt(pred.get("actual_finish") or pred.get("finish"))
    return dt(pred.get("actual_start") or pred.get("start"))


def driving_predecessor(task, by_uid, day_minutes=480.0):
    """The predecessor whose link lands latest on this task's start.

    The lag is converted on the successor's working day; a predecessor with no
    dates cannot drive. Returns (pred, link) or (None, None).
    """
    from datetime import timedelta
    best, best_link, best_when = None, None, None
    for link in task.get("predecessors") or []:
        pred = by_uid.get(link["predecessor_uid"])
        if pred is None or not considered(pred):
            continue
        when = link_target(pred, link)
        if when is None:
            continue
        when = when + timedelta(days=(link.get("lag_minutes") or 0.0) / day_minutes)
        if best_when is None or when > best_when:
            best, best_link, best_when = pred, link, when
    return best, best_link


def driving_chain(milestone, by_uid, cals, default_cal, slot):
    chain = []
    seen = set()
    node = milestone
    while node is not None and len(chain) < CHAIN_LIMIT and node["uid"] not in seen:
        seen.add(node["uid"])
        cal = cal_mod.resolve(cals, node.get("calendar_uid"), default_cal)
        bl = (node.get("baselines") or {}).get(slot) or {}
        bf, f = dt(bl.get("finish")), dt(node.get("actual_finish") or node.get("finish"))
        var = cal.working_days(bf, f) if (cal and bf and f) else ((f - bf).days if (bf and f) else None)
        chain.append({
            "id": node["id"], "uid": node["uid"], "name": node["name"],
            "finish": fmt(f), "baseline_finish": fmt(bf),
            "variance_days": var,
            "started": bool(node.get("actual_start")), "finished": bool(node.get("actual_finish")),
            "critical": bool(node.get("critical")),
        })
        if node.get("actual_finish"):
            break  # the past is not driving anything any more
        pred, link = driving_predecessor(node, by_uid, cal.day_minutes if cal else 480.0)
        if pred is None:
            chain[-1]["open_end"] = True
            break
        chain[-1]["via"] = link["type"]
        node = pred
    return chain


def delay_origin(chain):
    """The activity furthest from the milestone where the variance first appears.

    Walking from the milestone back along the chain, variance is inherited from
    the driver. The origin is the last node in the chain still carrying at least
    ORIGIN_MIN_DAYS of variance -- the deepest point where the slippage is present
    -- and the node after it is where it was absorbed or created.
    """
    origin = None
    for node in chain:
        v = node.get("variance_days")
        if v is not None and v >= ORIGIN_MIN_DAYS:
            origin = node
        elif origin is not None:
            break
    return origin


def delay_amplifier(chain):
    """The node where the variance grew most against its own driver.

    Where the variance first appears and where it grows most are different points
    on the chain, and the second is often the one worth a conversation: an origin
    of six days that a later activity turned into a hundred.
    """
    best, best_inc = None, 0
    for node, driver in zip(chain, chain[1:]):
        v, d = node.get("variance_days"), driver.get("variance_days")
        if v is None or d is None:
            continue
        inc = v - d
        if inc > best_inc:
            best, best_inc = node, inc
    if best is None and chain and (chain[-1].get("variance_days") or 0) > 0:
        best, best_inc = chain[-1], chain[-1]["variance_days"]
    return best, best_inc


def milestone_paths(model, cals, default_cal, slot):
    by_uid = {t["uid"]: t for t in model["tasks"]}
    status = dt(model["project"].get("status_date"))
    out = []
    for t in model["tasks"]:
        if not considered(t) or not t.get("milestone") or t.get("actual_finish"):
            continue
        f = dt(t.get("finish"))
        if status and f and f <= status:
            continue
        chain = driving_chain(t, by_uid, cals, default_cal, slot)
        origin = delay_origin(chain)
        amp, amp_inc = delay_amplifier(chain)
        out.append({
            "id": t["id"], "name": t["name"], "finish": fmt(f),
            "baseline_finish": chain[0]["baseline_finish"] if chain else None,
            "variance_days": chain[0]["variance_days"] if chain else None,
            "deadline": t.get("deadline"), "critical": bool(t.get("critical")),
            "chain_length": len(chain),
            "reaches_started": any(n["started"] for n in chain),
            "open_end": any(n.get("open_end") for n in chain),
            "origin": ({"id": origin["id"], "name": origin["name"],
                        "variance_days": origin["variance_days"], "started": origin["started"]}
                       if origin else None),
            "amplifier": ({"id": amp["id"], "name": amp["name"], "added_days": amp_inc}
                          if amp and amp_inc >= ORIGIN_MIN_DAYS else None),
            "chain": chain,
        })
    out.sort(key=lambda m: (-(m["variance_days"] or 0), m["finish"] or ""))
    return out


def calendar_forensics(model, cals, default_cal):
    """Reserve per year against activity-days per year, per calendar in use."""
    use = defaultdict(lambda: defaultdict(int))   # cal uid -> year -> activity-days
    for t in model["tasks"]:
        if not considered(t):
            continue
        cu = t.get("calendar_uid") if t.get("calendar_uid") in cals else default_cal
        s, f = dt(t.get("start")), dt(t.get("finish"))
        if not s or not f:
            continue
        y = s.year
        while y <= f.year:
            lo = max(s, datetime(y, 1, 1))
            hi = min(f, datetime(y, 12, 31))
            use[cu][y] += max(0, (hi - lo).days + 1)
            y += 1
    out = []
    for uid, cal in cals.items():
        if uid not in use:
            continue
        reserve = defaultdict(int)
        for day, ivs in cal.exception_intervals.items():
            if not ivs:
                reserve[day.year] += 1
        years = sorted(set(reserve) | set(use[uid]))
        rows = []
        flags = []
        for y in years:
            days, res = use[uid].get(y, 0), reserve.get(y, 0)
            rows.append({"year": y, "activity_days": days, "reserve_days": res})
            if days > 0 and res == 0 and any(reserve.values()):
                flags.append(f"{y}: activities without reserve")
            if res > 0 and days == 0:
                flags.append(f"{y}: reserve without activities")
        out.append({"uid": uid, "name": cal.name, "years": rows, "flags": flags})
    return out


def execution_pattern(model, res, slot, cals, default_cal):
    status = dt(model["project"].get("status_date"))
    by_uid = {t["uid"]: t for t in model["tasks"]}
    # out-of-sequence by month of the successor's actual start
    by_month = defaultdict(lambda: {"pairs": 0, "ignored": 0})
    for p in (res.get("pairs") or {}).get("A1", []):
        s = by_uid.get(p["successor_uid"])
        if s and s.get("actual_start"):
            by_month[s["actual_start"][:7]]["pairs"] += 1
    for p in (res.get("ignored") or {}).get("A1_both_complete", []):
        s = by_uid.get(p["successor_uid"])
        if s and s.get("actual_start"):
            by_month[s["actual_start"][:7]]["ignored"] += 1
    # start slippage
    slips = []
    for t in model["tasks"]:
        if not considered(t) or not t.get("actual_start"):
            continue
        bs = dt(((t.get("baselines") or {}).get(slot) or {}).get("start"))
        if bs:
            slips.append((dt(t["actual_start"]) - bs).days)
    slips.sort()

    def q(p):
        return slips[min(len(slips) - 1, max(0, int(round(p * (len(slips) - 1)))))] if slips else None

    return {
        "out_of_sequence_by_month": [{"period": m, **v} for m, v in sorted(by_month.items())],
        "start_slippage": {"sample": len(slips), "p20": q(0.2), "p50": q(0.5), "p80": q(0.8),
                           "started_early": sum(1 for s in slips if s < 0),
                           "started_late": sum(1 for s in slips if s > 0)},
    }


def cycle_forensics(model, prev, cmp_res, cals, default_cal, group_field):
    """Float consumed, activities that became critical, and milestone movement
    attributed to what moved on the driving chain."""
    if not prev:
        return None
    prev_by = {t["uid"]: t for t in prev["tasks"]}
    curr_by = {t["uid"]: t for t in model["tasks"]}

    def mpd(t):
        c = cal_mod.resolve(cals, t.get("calendar_uid"), default_cal)
        return c.day_minutes if c else 480.0

    def group_of(t):
        if group_field:
            return (t.get("custom") or {}).get(group_field) or "(unassigned)"
        return (t.get("outline_number") or "").split(".")[0] or "(unassigned)"

    consumed = []
    by_group = defaultdict(lambda: {"activities": 0, "float_consumed_days": 0.0})
    became_critical = []
    for uid, c in curr_by.items():
        p = prev_by.get(uid)
        if p is None or not considered(c) or c.get("actual_finish"):
            continue
        cs, ps = c.get("total_slack_minutes"), p.get("total_slack_minutes")
        if cs is None or ps is None:
            continue
        d = (ps - cs) / mpd(c)
        g = group_of(c)
        by_group[g]["activities"] += 1
        by_group[g]["float_consumed_days"] += d
        if d >= 1:
            consumed.append({"id": c["id"], "name": c["name"], "group": g,
                             "float_before": round(ps / mpd(c), 1), "float_now": round(cs / mpd(c), 1),
                             "consumed": round(d, 1)})
        if ps > 0 and cs <= 0:
            became_critical.append({"id": c["id"], "name": c["name"], "group": g,
                                    "float_before": round(ps / mpd(c), 1)})
    consumed.sort(key=lambda x: -x["consumed"])

    readings = {}
    for kind in ("execution", "replan"):
        for tr in (cmp_res or {}).get("trend", []):
            if tr["reading"] == kind:
                readings[tr["uid"]] = kind
    for bm in (cmp_res or {}).get("baseline_moved", []):
        readings[bm["uid"]] = "reference"

    slot = (model.get("prevailing_baseline") or {}).get("slot")
    movements = []
    for m in milestone_paths(model, cals, default_cal, slot):
        p = prev_by.get(next((n["uid"] for n in m["chain"] if n["id"] == m["id"]), None))
        pf = dt(p.get("finish")) if p else None
        cf = dt(m["finish"])
        if not pf or not cf:
            continue
        moved = (cf - pf).days
        drivers = [{"id": n["id"], "name": n["name"], "reading": readings.get(n["uid"])}
                   for n in m["chain"] if readings.get(n["uid"])]
        movements.append({"id": m["id"], "name": m["name"], "finish_before": fmt(pf),
                          "finish_now": fmt(cf), "moved_days": moved,
                          "chain_moves": drivers[:10],
                          "attribution": (max(set(x["reading"] for x in drivers),
                                              key=[x["reading"] for x in drivers].count)
                                          if drivers else ("none" if moved == 0 else "outside the chain"))})
    movements.sort(key=lambda x: -abs(x["moved_days"]))
    return {
        "float_consumed": consumed[:200],
        "float_by_group": sorted(
            [{"group": g, **v, "float_consumed_days": round(v["float_consumed_days"], 1)}
             for g, v in by_group.items()], key=lambda r: -r["float_consumed_days"]),
        "became_critical": became_critical[:200],
        "milestone_movements": movements[:80],
    }


def build(model, res, prev=None, cmp_res=None, group_field=None):
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    cal_blob = model.get("calendars") or {}
    cals = cal_mod.from_dict(cal_blob.get("definitions"))
    default_cal = cal_blob.get("default_uid")
    if cals:
        stamps = [dt(v) for t in model["tasks"] for v in (t.get("start"), t.get("finish")) if v]
        if stamps:
            cal_mod.prepare(cals, min(stamps).date(), max(stamps).date())
    paths = milestone_paths(model, cals, default_cal, slot)
    return {
        "status_date": model["project"].get("status_date"),
        "milestones": paths,
        "summary": {
            "milestones": len(paths),
            "with_origin": sum(1 for m in paths if m["origin"]),
            "open_ended_chains": sum(1 for m in paths if m["open_end"]),
            # The activities that originate delay on the most milestones: one name
            # can be the root of a dozen slipped dates.
            "origins": sorted(
                [{"id": k[0], "name": k[1], "milestones": v} for k, v in _count_origins(paths).items()],
                key=lambda x: -x["milestones"])[:15],
        },
        "calendars": calendar_forensics(model, cals, default_cal),
        "execution": execution_pattern(model, res, slot, cals, default_cal),
        "cycle": cycle_forensics(model, prev, cmp_res, cals, default_cal, group_field),
        "provenance": "mechanism reconstruction from the file's dates, links and calendars; "
                      "not a contractual delay analysis, which needs contemporaneous records",
    }


def _count_origins(paths):
    c = defaultdict(int)
    for m in paths:
        if m["origin"]:
            c[(m["origin"]["id"], m["origin"]["name"])] += 1
    return c


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model")
    ap.add_argument("findings")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--previous")
    ap.add_argument("--cycle")
    ap.add_argument("--group-field")
    args = ap.parse_args()
    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    with open(args.findings, encoding="utf-8") as fh:
        res = json.load(fh)
    prev = cmp = None
    if args.previous:
        with open(args.previous, encoding="utf-8") as fh:
            prev = json.load(fh)
    if args.cycle:
        with open(args.cycle, encoding="utf-8") as fh:
            cmp = json.load(fh)
    out = build(model, res, prev, cmp, args.group_field)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    s = out["summary"]
    print(f"{s['milestones']} milestones, {s['with_origin']} with a named origin, "
          f"{s['open_ended_chains']} open-ended chains -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
