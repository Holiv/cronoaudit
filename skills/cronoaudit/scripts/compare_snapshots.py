#!/usr/bin/env python3
"""Compare two snapshots of the SAME schedule -- previous delivery against current.

    python3 parse_mspdi.py previous.xml -o prev.json
    python3 parse_mspdi.py current.xml  -o curr.json
    python3 compare_snapshots.py prev.json curr.json --json cycle.json

The question is not "is this file consistent" (run_checks.py answers that). It is
"what moved since last time, and was it the works that moved or the plan?"

Two rules govern this file:

* Both snapshots' aggregate figures come from ONE function called twice. Do not
  verify that the two halves agree -- construct them so they cannot disagree. Two
  code paths pass their comparison test until somebody edits one of them.
* A changed baseline is a finding ABOUT THE REPORT, not about performance. Every
  deviation that straddles the change is measured against two references.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

EPS = 1e-4


def dt(v):
    return datetime.fromisoformat(v) if v else None


def days_between(a, b):
    a, b = dt(a), dt(b)
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 86400.0, 1)


def considered(t) -> bool:
    """Leaf, active, not external, not a milestone.

    Summaries would double-count their children. Milestones have no duration, so
    they distort every rate -- and their cost legitimately sits outside a phased
    curve, which is a separate finding rather than an input here.
    """
    return (
        not t.get("summary")
        and t.get("active") is not False
        and not t.get("external")
        and not t.get("milestone")
    )


def snapshot_aggregate(model: dict) -> dict:
    """The aggregate figures for ONE snapshot.

    Called once per snapshot, from the same code, so the previous cycle's number
    cannot have been produced by a different rule from the current one. That is
    the cheapest available guarantee that both halves of the comparison share a
    reference -- and the difference between two figures built by two rules is a
    datum artefact that reads as performance.
    """
    slot = (model.get("prevailing_baseline") or {}).get("slot")
    planned = earned = 0.0
    leaves = 0
    for t in model["tasks"]:
        if not considered(t):
            continue
        bl = (t.get("baselines") or {}).get(slot) if slot else None
        bcost = (bl or {}).get("cost") or 0.0
        if bcost <= 0:
            continue
        leaves += 1
        phys = t.get("physical_percent_complete")
        if phys is None:
            phys = t.get("percent_complete") or 0.0
        planned += bcost
        earned += bcost * (phys / 100.0)
    return {
        "baseline_slot": slot,
        "budget_at_completion": round(planned, 2),
        "earned": round(earned, 2),
        "percent_earned": round(earned / planned * 100, 4) if planned else None,
        "leaves_with_baseline_cost": leaves,
        "status_date": model["project"].get("status_date"),
        "percent_source": "physical percent complete, falling back to percent complete",
    }


def index_by_name_wbs(tasks) -> dict:
    idx = {}
    for t in tasks:
        key = f"{t.get('name')}|{t.get('wbs')}"
        idx.setdefault(key, t)
    return idx


def match(prev_tasks, curr_tasks):
    """Two-step cascade, then two classes -- and only two.

    1. the stable unique identifier
    2. failing that, name plus WBS path

    A renamed activity that also moved branch is indistinguishable from a removal
    plus an insertion. Inventing a third class would assert something unverifiable,
    so the unmatched count is reported as a number a person must judge.

    The phantom row representing an inserted subproject carries a FILE-LOCAL
    identifier: matching across files on it resolves to the wrong pair rather than
    to nothing, which is worse than failing. Those rows are excluded by
    `considered` along with other summaries.
    """
    by_uid = {t["uid"]: t for t in prev_tasks}
    by_name = index_by_name_wbs(prev_tasks)
    pairs, inserted, used = [], [], set()

    for c in curr_tasks:
        p = by_uid.get(c["uid"])
        how = "uid"
        if p is None:
            p = by_name.get(f"{c.get('name')}|{c.get('wbs')}")
            how = "name+wbs"
        if p is None:
            if considered(c):
                inserted.append(c)
            continue
        used.add(p["uid"])
        pairs.append((p, c, how))

    removed = [p for p in prev_tasks if p["uid"] not in used and considered(p)]
    return pairs, inserted, removed


def compare(prev: dict, curr: dict) -> dict:
    agg_prev = snapshot_aggregate(prev)
    agg_curr = snapshot_aggregate(curr)
    pairs, inserted, removed = match(prev["tasks"], curr["tasks"])

    slot = agg_curr["baseline_slot"]
    trend, baseline_moved, decomposition = [], [], []

    for p, c, how in pairs:
        if not considered(c):
            continue

        moved_start = days_between(p.get("start"), c.get("start"))
        moved_finish = days_between(p.get("finish"), c.get("finish"))
        if (moved_start or 0) or (moved_finish or 0):
            has_actuals = bool(c.get("actual_start") or c.get("actual_finish"))
            trend.append({
                "uid": c["uid"], "id": c["id"], "name": c["name"], "matched_by": how,
                "start_moved_days": moved_start, "finish_moved_days": moved_finish,
                "actuals_present": has_actuals,
                # The discriminator. Dates moving with actuals behind them is the
                # works behaving differently; dates moving with none is a rewritten
                # forecast. Both are legitimate; only one is execution.
                "reading": "execution" if has_actuals else "replan",
            })

        bp = (p.get("baselines") or {}).get(slot) or {}
        bc = (c.get("baselines") or {}).get(slot) or {}
        bs = days_between(bp.get("start"), bc.get("start"))
        bf = days_between(bp.get("finish"), bc.get("finish"))
        if (bs or 0) or (bf or 0):
            baseline_moved.append({
                "uid": c["uid"], "id": c["id"], "name": c["name"],
                "baseline_start_moved_days": bs, "baseline_finish_moved_days": bf,
                "slot": slot,
            })

    # Weight-relative decomposition against the CURRENT snapshot's budget, so the
    # contributions sum to the aggregate deviation instead of merely correlating
    # with it. State the denominator: a decomposition against a different one is
    # not comparable with last cycle's.
    denom = agg_curr["budget_at_completion"]
    total = 0.0
    if denom:
        for p, c, _ in pairs:
            if not considered(c):
                continue
            bc = (c.get("baselines") or {}).get(slot) or {}
            bcost = bc.get("cost") or 0.0
            if bcost <= 0:
                continue
            phys_c = c.get("physical_percent_complete")
            if phys_c is None:
                phys_c = c.get("percent_complete") or 0.0
            phys_p = p.get("physical_percent_complete")
            if phys_p is None:
                phys_p = p.get("percent_complete") or 0.0
            contribution = bcost * (phys_c - phys_p) / 100.0 / denom * 100.0
            if abs(contribution) >= EPS:
                total += contribution
                decomposition.append({
                    "uid": c["uid"], "id": c["id"], "name": c["name"],
                    "wbs": c.get("wbs"),
                    "percent_previous": phys_p, "percent_current": phys_c,
                    "baseline_cost": bcost,
                    "contribution_points": round(contribution, 4),
                })
    decomposition.sort(key=lambda d: abs(d["contribution_points"]), reverse=True)

    warnings = []
    if baseline_moved:
        warnings.append(
            f"The baseline moved on {len(baseline_moved)} activities between these two "
            "snapshots. Your comparison basis changed underneath the comparison: every "
            "deviation straddling the change is measured against two references. Report "
            "this as a finding about the report, not as performance."
        )
    if agg_prev["baseline_slot"] != agg_curr["baseline_slot"]:
        warnings.append(
            f"The prevailing baseline slot differs between snapshots "
            f"({agg_prev['baseline_slot']} then {agg_curr['baseline_slot']}). The two "
            "aggregate figures are not comparable until one slot is chosen for both."
        )
    if inserted or removed:
        warnings.append(
            f"{len(inserted)} activities inserted and {len(removed)} removed. Scope "
            "changed, so the aggregate movement is not purely progress."
        )
    if agg_curr["leaves_with_baseline_cost"] == 0:
        warnings.append("No leaf carries baseline cost, so there is no weight to decompose.")

    result = {
        "previous": {"source": prev.get("source"), **agg_prev},
        "current": {"source": curr.get("source"), **agg_curr},
        "movement_points": (
            round(agg_curr["percent_earned"] - agg_prev["percent_earned"], 4)
            if agg_curr["percent_earned"] is not None and agg_prev["percent_earned"] is not None
            else None
        ),
        "decomposition_sums_to_points": round(total, 4),
        # The gap between the headline movement and the sum of the per-activity
        # contributions. It is NOT rounding: it is everything that moved the
        # aggregate without being progress -- scope inserted or removed changing
        # the denominator, a rebased baseline, a slot change. Naming it is the
        # point. An unnamed residue is where a plausible wrong number lives.
        "movement_unexplained_points": None,
        "conventions": {
            "matching": "stable UID, then name plus WBS path; two classes only",
            "population": "leaf, active, non-external, non-milestone",
            "denominator": "current snapshot budget at completion",
            "aggregates": "both snapshots computed by one function called twice",
        },
        "warnings": warnings,
        "trend": trend,
        "baseline_moved": baseline_moved,
        "unmatched": {
            "inserted": [{"uid": t["uid"], "id": t["id"], "name": t["name"]} for t in inserted],
            "removed": [{"uid": t["uid"], "id": t["id"], "name": t["name"]} for t in removed],
        },
        "decomposition": decomposition,
    }
    if result["movement_points"] is not None:
        gap = round(result["movement_points"] - total, 4)
        result["movement_unexplained_points"] = gap
        if abs(gap) >= 0.01:
            result["warnings"].append(
                f"{gap:+.4f} percentage points of the movement are NOT explained by "
                "per-activity progress. Something other than work done moved the "
                "aggregate: scope changing the denominator, a rebased baseline, or a "
                "different baseline slot. Do not report the headline movement as "
                "progress until this residue is accounted for."
            )
    return result


def report(r: dict) -> str:
    L = ["Cycle comparison", ""]
    L.append(f"  previous  {r['previous']['source']}  status {r['previous']['status_date']}")
    L.append(f"  current   {r['current']['source']}  status {r['current']['status_date']}")
    L.append("")
    L.append(f"  earned    {r['previous']['percent_earned']}%  ->  {r['current']['percent_earned']}%")
    L.append(f"  movement  {r['movement_points']} percentage points")
    L.append(f"  decomposition sums to {r['decomposition_sums_to_points']} points")
    L.append(f"  unexplained residue  {r['movement_unexplained_points']} points")
    L.append("")
    exec_n = sum(1 for t in r["trend"] if t["reading"] == "execution")
    replan_n = sum(1 for t in r["trend"] if t["reading"] == "replan")
    L += [
        "  dates moved:",
        f"    {exec_n} with actuals behind them        -> execution",
        f"    {replan_n} with no actuals                -> replan",
        f"    {len(r['baseline_moved'])} with the BASELINE itself moved  -> the reference moved",
        "",
        f"  scope: {len(r['unmatched']['inserted'])} inserted, {len(r['unmatched']['removed'])} removed",
        "",
    ]
    if r["warnings"]:
        L.append("  WARNINGS:")
        L += [f"    * {w}" for w in r["warnings"]]
        L.append("")
    if r["decomposition"]:
        L.append("  largest contributions to the movement:")
        for d in r["decomposition"][:10]:
            L.append(
                f"    {d['contribution_points']:+8.4f} pp  id {d['id']:<5} "
                f"{d['percent_previous']:>5.1f}% -> {d['percent_current']:>5.1f}%  {d['name']}"
            )
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("previous", help="JSON model of the earlier snapshot")
    ap.add_argument("current", help="JSON model of the later snapshot")
    ap.add_argument("--json", help="write the full comparison here")
    args = ap.parse_args()

    with open(args.previous, encoding="utf-8") as fh:
        prev = json.load(fh)
    with open(args.current, encoding="utf-8") as fh:
        curr = json.load(fh)
    res = compare(prev, curr)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, ensure_ascii=False)
        print(f"comparison -> {args.json}", file=sys.stderr)
    print(report(res))


if __name__ == "__main__":
    main()
