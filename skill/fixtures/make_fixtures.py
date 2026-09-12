#!/usr/bin/env python3
"""Generate the synthetic MSPDI fixtures the checks are tested against.

Two files, and both halves matter:

  positive.xml -- every check has at least one activity it MUST flag
  negative.xml -- a consistent schedule where every check MUST stay silent

The negative half is not optional. A check that never fires proves nothing, and
a probe that cannot pass makes a clean result meaningless. Proving the
instrument can fire, and can also stay quiet, is what makes a "no findings"
answer worth anything.

No real schedule data. Synthetic throughout.
"""
from __future__ import annotations

import os

NS = "http://schemas.microsoft.com/project"
STATUS = "2026-06-30T17:00:00"
MPD = 480


def task(uid, tid, name, **kw):
    """Build one <Task>. Absent keys are omitted, never emitted empty."""
    parts = [
        f"    <UID>{uid}</UID>",
        f"    <ID>{tid}</ID>",
        f"    <Name>{name}</Name>",
        f"    <WBS>{kw.get('wbs', tid)}</WBS>",
        f"    <OutlineLevel>{kw.get('level', 2)}</OutlineLevel>",
        f"    <Summary>{1 if kw.get('summary') else 0}</Summary>",
        f"    <Milestone>{1 if kw.get('milestone') else 0}</Milestone>",
        "    <Active>1</Active>",
        "    <ExternalTask>0</ExternalTask>",
    ]
    for tag, key in (
        ("Start", "start"), ("Finish", "finish"),
        ("ActualStart", "astart"), ("ActualFinish", "afinish"),
        ("Deadline", "deadline"),
    ):
        if kw.get(key):
            parts.append(f"    <{tag}>{kw[key]}</{tag}>")
    if kw.get("dur_hours") is not None:
        parts.append(f"    <Duration>PT{kw['dur_hours']}H0M0S</Duration>")
    if kw.get("pct") is not None:
        parts.append(f"    <PercentComplete>{kw['pct']}</PercentComplete>")
    if kw.get("phys") is not None:
        parts.append(f"    <PhysicalPercentComplete>{kw['phys']}</PhysicalPercentComplete>")
    if kw.get("slack_days") is not None:
        parts.append(f"    <TotalSlack>{int(kw['slack_days'] * MPD * 10)}</TotalSlack>")
    for pred in kw.get("preds", []):
        puid, ptype, lag_days = pred
        parts += [
            "    <PredecessorLink>",
            f"      <PredecessorUID>{puid}</PredecessorUID>",
            f"      <Type>{ptype}</Type>",
            f"      <LinkLag>{int(lag_days * MPD * 10)}</LinkLag>",
            "      <LagFormat>7</LagFormat>",
            "    </PredecessorLink>",
        ]
    bl = kw.get("baseline")
    if bl:
        bstart, bfinish, bcost, bhours = bl
        parts += [
            "    <Baseline>",
            f"      <Number>{kw.get('bl_slot', 1)}</Number>",
            f"      <Start>{bstart}</Start>",
            f"      <Finish>{bfinish}</Finish>",
            f"      <Duration>PT{bhours}H0M0S</Duration>",
            f"      <Cost>{bcost}</Cost>",
            f"      <Work>PT{bhours}H0M0S</Work>",
            "    </Baseline>",
        ]
    return "  <Task>\n" + "\n".join(parts) + "\n  </Task>"


def document(name, tasks):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Project xmlns="{NS}">\n'
        f"  <Name>{name}</Name>\n"
        f"  <Title>{name}</Title>\n"
        f"  <StatusDate>{STATUS}</StatusDate>\n"
        f"  <CurrentDate>{STATUS}</CurrentDate>\n"
        f"  <MinutesPerDay>{MPD}</MinutesPerDay>\n"
        "  <MinutesPerWeek>2400</MinutesPerWeek>\n"
        "  <DaysPerMonth>20</DaysPerMonth>\n"
        "  <Tasks>\n" + "\n".join(tasks) + "\n  </Tasks>\n"
        "</Project>\n"
    )


# A consistent five-day working window used wherever nothing should be flagged.
WIN = dict(start="2026-03-02T08:00:00", finish="2026-03-06T17:00:00", dur_hours=40)
BL_OK = ("2026-03-02T08:00:00", "2026-03-06T17:00:00", 10000.0, 40)


def positive():
    t = []
    # A1 -- successor started, predecessor not finished. Both ends must be marked.
    t.append(task(1, 1, "A1 predecessor not finished", **WIN,
                  astart="2026-03-02T08:00:00", pct=40, baseline=BL_OK))
    t.append(task(2, 2, "A1 successor started early", **WIN,
                  astart="2026-03-04T08:00:00", pct=30, baseline=BL_OK,
                  preds=[(1, 1, 0)]))
    # A2 -- total inversion: successor finished, predecessor never started.
    t.append(task(3, 3, "A2 predecessor never started", **WIN, baseline=BL_OK))
    t.append(task(4, 4, "A2 successor complete", **WIN,
                  astart="2026-03-02T08:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, baseline=BL_OK, preds=[(3, 1, 0)]))
    # H -- finish elapsed before the status date with no actuals at all.
    t.append(task(5, 5, "H elapsed with no progress", **WIN, baseline=BL_OK))
    # E -- pulled forward well beyond threshold, never started.
    t.append(task(6, 6, "E pulled forward", start="2026-03-02T08:00:00",
                  finish="2026-03-06T17:00:00", dur_hours=40,
                  baseline=("2026-08-03T08:00:00", "2026-08-07T17:00:00", 10000.0, 40)))
    # C -- delayed well beyond threshold.
    t.append(task(7, 7, "C delayed", start="2026-08-03T08:00:00",
                  finish="2026-08-07T17:00:00", dur_hours=40,
                  baseline=("2026-03-02T08:00:00", "2026-03-06T17:00:00", 10000.0, 40)))
    # G -- duration far wider than the start-to-finish window.
    t.append(task(8, 8, "G duration disagrees", start="2026-03-02T08:00:00",
                  finish="2026-03-06T17:00:00", dur_hours=160, baseline=BL_OK))
    # B -- milestone with no deadline.
    t.append(task(9, 9, "B milestone no deadline", milestone=True,
                  start="2026-03-06T17:00:00", finish="2026-03-06T17:00:00",
                  dur_hours=0, baseline=("2026-03-06T17:00:00",
                                         "2026-03-06T17:00:00", 500.0, 0)))
    # F -- in progress with percent complete at zero.
    t.append(task(10, 10, "F in progress at zero", **WIN,
                  astart="2026-03-02T08:00:00", pct=0, baseline=BL_OK))
    # P -- declared complete with no actual finish.
    t.append(task(11, 11, "P pending record", **WIN,
                  astart="2026-03-02T08:00:00", pct=100, phys=100, baseline=BL_OK))
    # The migration rule: task 11 is a predecessor of 12, and 12 has started.
    # That is NOT an A1 breach -- 11 is a record defect and already sits in P.
    t.append(task(12, 12, "P successor must not raise A1", **WIN,
                  astart="2026-03-04T08:00:00", pct=20, baseline=BL_OK,
                  preds=[(11, 1, 0)]))
    return document("Positive fixture", t)


def negative():
    """A consistent schedule. Every check must stay silent on this file."""
    t = []
    # Finished cleanly, in sequence, on the baseline window.
    t.append(task(1, 1, "Finished in sequence", **WIN,
                  astart="2026-03-02T08:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, baseline=BL_OK))
    t.append(task(2, 2, "Successor after predecessor finished",
                  start="2026-03-09T08:00:00", finish="2026-03-13T17:00:00",
                  dur_hours=40, astart="2026-03-09T08:00:00",
                  afinish="2026-03-13T17:00:00", pct=100, phys=100,
                  baseline=("2026-03-09T08:00:00", "2026-03-13T17:00:00", 10000.0, 40),
                  preds=[(1, 1, 0)]))
    # In progress, reported, not yet due.
    t.append(task(3, 3, "In progress, future finish",
                  start="2026-06-29T08:00:00", finish="2026-07-03T17:00:00",
                  dur_hours=40, astart="2026-06-29T08:00:00", pct=35,
                  baseline=("2026-06-29T08:00:00", "2026-07-03T17:00:00", 8000.0, 40)))
    # Future work, not started, on plan.
    t.append(task(4, 4, "Future work on plan",
                  start="2026-07-06T08:00:00", finish="2026-07-10T17:00:00",
                  dur_hours=40,
                  baseline=("2026-07-06T08:00:00", "2026-07-10T17:00:00", 9000.0, 40)))
    # Milestone WITH a deadline.
    t.append(task(5, 5, "Milestone with deadline", milestone=True,
                  start="2026-07-10T17:00:00", finish="2026-07-10T17:00:00",
                  dur_hours=0, deadline="2026-07-10T17:00:00",
                  baseline=("2026-07-10T17:00:00", "2026-07-10T17:00:00", 500.0, 0)))
    return document("Negative fixture", t)


def cycle(which: str):
    """A pair of snapshots of the SAME schedule, for the comparator.

    Built so each of the three readings has exactly one instance:
      uid 2  progressed with actuals behind it        -> execution
      uid 3  finish pushed with NO actuals            -> replan
      uid 4  the BASELINE itself moved                -> the reference moved
      uid 5  present only in current                  -> inserted
      uid 6  present only in previous                 -> removed
    """
    prev = which == "prev"
    t = []
    t.append(task(1, 1, "Complete both cycles", **WIN,
                  astart="2026-03-02T08:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, baseline=BL_OK))
    # Execution: real progress, actual start present in both.
    t.append(task(2, 2, "Progressed with actuals",
                  start="2026-06-01T08:00:00",
                  finish="2026-07-03T17:00:00" if prev else "2026-07-10T17:00:00",
                  dur_hours=160, astart="2026-06-01T08:00:00",
                  pct=30 if prev else 55, phys=30 if prev else 55,
                  baseline=("2026-06-01T08:00:00", "2026-07-03T17:00:00", 40000.0, 160)))
    # Replan: the forecast moved a month with nothing executed behind it.
    t.append(task(3, 3, "Forecast pushed, nothing executed",
                  start="2026-07-06T08:00:00" if prev else "2026-08-03T08:00:00",
                  finish="2026-07-17T17:00:00" if prev else "2026-08-14T17:00:00",
                  dur_hours=80,
                  baseline=("2026-07-06T08:00:00", "2026-07-17T17:00:00", 20000.0, 80)))
    # The reference moved: same dates, different BASELINE.
    t.append(task(4, 4, "Baseline rebased",
                  start="2026-07-20T08:00:00", finish="2026-07-31T17:00:00",
                  dur_hours=80,
                  baseline=(("2026-07-20T08:00:00", "2026-07-31T17:00:00", 15000.0, 80)
                            if prev else
                            ("2026-08-17T08:00:00", "2026-08-28T17:00:00", 15000.0, 80))))
    if not prev:
        t.append(task(5, 5, "Inserted this cycle",
                      start="2026-09-01T08:00:00", finish="2026-09-04T17:00:00",
                      dur_hours=32,
                      baseline=("2026-09-01T08:00:00", "2026-09-04T17:00:00", 5000.0, 32)))
    if prev:
        t.append(task(6, 6, "Removed this cycle",
                      start="2026-09-07T08:00:00", finish="2026-09-11T17:00:00",
                      dur_hours=40,
                      baseline=("2026-09-07T08:00:00", "2026-09-11T17:00:00", 7000.0, 40)))
    return document(f"Cycle fixture {which}", t)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    for fname, body in (("positive.xml", positive()), ("negative.xml", negative()),
                        ("cycle_prev.xml", cycle("prev")), ("cycle_curr.xml", cycle("curr"))):
        path = os.path.join(here, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
