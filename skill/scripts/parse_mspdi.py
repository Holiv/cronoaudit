#!/usr/bin/env python3
"""Parse an MS Project XML (MSPDI) export into a canonical JSON model.

MSPDI is Project's own documented interchange format: File > Save As > XML.
It is text, it is a general Project standard rather than any organisation's
convention, and it needs no library. This script is stdlib-only on purpose.

Usage:
    python3 parse_mspdi.py schedule.xml                 # JSON to stdout
    python3 parse_mspdi.py schedule.xml -o model.json

Unit handling is the point of this file. Read `units()` before trusting a number.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime

import calendars as cal_mod
import custom_fields as cf_mod

NS = {"p": "http://schemas.microsoft.com/project"}

# MSPDI stores these as tenths of a minute, not minutes and not days.
TENTHS_FIELDS = {"TotalSlack", "FreeSlack", "StartSlack", "FinishSlack", "LinkLag"}

LINK_TYPE = {"0": "FF", "1": "FS", "2": "SF", "3": "SS"}

_ISO_DUR = re.compile(
    r"^(?P<sign>-)?P"
    r"(?:(?P<years>\d+(?:\.\d+)?)Y)?"
    r"(?:(?P<months>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<weeks>\d+(?:\.\d+)?)W)?"
    r"(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
    r")?$"
)


def text(node, tag: str):
    """Return the stripped text of a child element, or None when absent/empty."""
    if node is None:
        return None
    el = node.find(f"p:{tag}", NS)
    if el is None or el.text is None:
        return None
    val = el.text.strip()
    return val or None


def as_int(node, tag: str):
    raw = text(node, tag)
    if raw is None:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def as_float(node, tag: str):
    raw = text(node, tag)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def as_bool(node, tag: str):
    raw = text(node, tag)
    if raw is None:
        return None
    return raw in ("1", "true", "True")


def as_date(node, tag: str):
    """MSPDI datetimes are local with no timezone. Absent means absent -- never today."""
    raw = text(node, tag)
    if raw is None:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return None


def iso_duration_minutes(raw):
    """ISO 8601 duration -> minutes of work.

    MSPDI writes durations as PT40H0M0S, not as a day count and not as minutes.
    Year and month components are not convertible without a calendar, so they
    are rejected rather than guessed; Project does not emit them for durations.
    """
    if raw is None:
        return None
    m = _ISO_DUR.match(raw.strip())
    if not m:
        return None
    g = {k: float(v) for k, v in m.groupdict().items() if v and k != "sign"}
    if g.get("years") or g.get("months"):
        return None
    minutes = (
        g.get("weeks", 0) * 7 * 24 * 60
        + g.get("days", 0) * 24 * 60
        + g.get("hours", 0) * 60
        + g.get("minutes", 0)
        + g.get("seconds", 0) / 60
    )
    return -minutes if m.group("sign") else minutes


def tenths_to_minutes(raw):
    """Slack and lag fields arrive as tenths of a minute."""
    if raw is None:
        return None
    try:
        return float(raw) / 10.0
    except ValueError:
        return None


def units(root) -> dict:
    """The conversion basis, read from the file rather than assumed.

    Never hardcode 480. Works run 8, 9 and 10-hour days and shifts, and every
    duration, variance, slack and lag in the file is expressed against whatever
    this says.
    """
    mpd = as_float(root, "MinutesPerDay")
    mpw = as_float(root, "MinutesPerWeek")
    return {
        "minutes_per_day": mpd,
        "minutes_per_week": mpw,
        "days_per_month": as_float(root, "DaysPerMonth"),
        "minutes_per_day_assumed": mpd is None,
        "note": (
            "Durations are ISO 8601 in MSPDI; slack and lag are tenths of a minute. "
            "Day counts are derived from minutes_per_day, which is the configured "
            "working day, not 1440."
        ),
    }


def parse_baselines(task_el) -> dict:
    """Baseline slots present on this task, keyed by slot number as a string.

    Project keeps eleven slots. Which one is current is not reliably declared,
    so the model records every slot it finds and leaves the choice to the caller.
    """
    out = {}
    for bl in task_el.findall("p:Baseline", NS):
        number = text(bl, "Number") or "0"
        out[number] = {
            "start": as_date(bl, "Start"),
            "finish": as_date(bl, "Finish"),
            "duration_minutes": iso_duration_minutes(text(bl, "Duration")),
            "cost": as_float(bl, "Cost"),
            "work_minutes": iso_duration_minutes(text(bl, "Work")),
        }
    return out


def parse_links(task_el) -> list:
    out = []
    for ln in task_el.findall("p:PredecessorLink", NS):
        lag_fmt = text(ln, "LagFormat")
        out.append(
            {
                "predecessor_uid": as_int(ln, "PredecessorUID"),
                "type": LINK_TYPE.get(text(ln, "Type") or "1", "FS"),
                "lag_minutes": tenths_to_minutes(text(ln, "LinkLag")),
                "lag_format": lag_fmt,
            }
        )
    return out


def parse_task(task_el) -> dict:
    return {
        "uid": as_int(task_el, "UID"),
        # The visible row number. Renumbers freely, so never join on it -- but it
        # is the only identifier a person can see on their screen, so keep it.
        "id": as_int(task_el, "ID"),
        "name": text(task_el, "Name"),
        "wbs": text(task_el, "WBS"),
        "outline_number": text(task_el, "OutlineNumber"),
        "outline_level": as_int(task_el, "OutlineLevel"),
        # Which calendar governs THIS task. "-1" or absent means the project default.
        # Every duration and span on this task is expressed against it.
        "calendar_uid": text(task_el, "CalendarUID"),
        "summary": as_bool(task_el, "Summary"),
        "milestone": as_bool(task_el, "Milestone"),
        "active": as_bool(task_el, "Active"),
        "external": as_bool(task_el, "ExternalTask"),
        "start": as_date(task_el, "Start"),
        "finish": as_date(task_el, "Finish"),
        "actual_start": as_date(task_el, "ActualStart"),
        "actual_finish": as_date(task_el, "ActualFinish"),
        "deadline": as_date(task_el, "Deadline"),
        "constraint_type": as_int(task_el, "ConstraintType"),
        "duration_minutes": iso_duration_minutes(text(task_el, "Duration")),
        "percent_complete": as_float(task_el, "PercentComplete"),
        # Different field from percent_complete, and the one earned value needs.
        # Frequently absent, which is itself worth reporting.
        "physical_percent_complete": as_float(task_el, "PhysicalPercentComplete"),
        "percent_work_complete": as_float(task_el, "PercentWorkComplete"),
        "total_slack_minutes": tenths_to_minutes(text(task_el, "TotalSlack")),
        "cost": as_float(task_el, "Cost"),
        "fixed_cost": as_float(task_el, "FixedCost"),
        "baselines": parse_baselines(task_el),
        "predecessors": parse_links(task_el),
        # Custom field values, keyed by the STABLE field id. Field names arrive
        # translated by the installed language, so the id is the only safe key.
        "custom": {
            text(ea, "FieldID"): text(ea, "Value")
            for ea in task_el.findall("p:ExtendedAttribute", NS)
            if text(ea, "FieldID") and text(ea, "Value")
        },
    }


def prevailing_baseline(tasks) -> dict:
    """Derive the live baseline slot from the data, not from a declared field.

    The setting that names the earned-value baseline is not dependable, so the
    slot is elected: the highest-numbered slot with any leaf task carrying cost
    above zero. Summary rows and external tasks do not vote -- they hold
    rolled-up or foreign values and would elect a slot that holds nothing.
    """
    evidence = {}
    for t in tasks:
        if t["summary"] or t["external"]:
            continue
        for slot, bl in t["baselines"].items():
            if (bl.get("cost") or 0) > 0:
                evidence[slot] = evidence.get(slot, 0) + 1
    if not evidence:
        return {"slot": None, "leaves_with_cost": {}, "basis": "no baseline cost found"}
    slot = max(evidence, key=lambda s: int(s))
    return {
        "slot": slot,
        "leaves_with_cost": dict(sorted(evidence.items(), key=lambda kv: int(kv[0]))),
        "basis": "highest-numbered slot with leaf cost > 0; summaries and external tasks excluded",
    }


def parse(path: str) -> dict:
    root = ET.parse(path).getroot()
    if not root.tag.endswith("Project"):
        raise SystemExit(f"{path}: root element is {root.tag!r}, not a Project XML export")

    tasks = [parse_task(t) for t in root.findall("p:Tasks/p:Task", NS)]
    tasks = [t for t in tasks if t["uid"] is not None]

    # Calendars are not optional context: a construction schedule keeps its
    # holidays, its shift length and its weather reserve in them, and they differ
    # per task. See scripts/calendars.py for what assuming a five-day week cost.
    cals = cal_mod.parse_calendars(root)
    default_cal = text(root, "CalendarUID")
    for t in tasks:
        if not t["calendar_uid"] or t["calendar_uid"] == "-1":
            t["calendar_uid"] = default_cal
    used = Counter(t["calendar_uid"] for t in tasks)

    status_date = as_date(root, "StatusDate")
    return {
        "source": path,
        "project": {
            "name": text(root, "Name"),
            "title": text(root, "Title"),
            # No status date is a hard stop for the checks, not a default to today.
            "status_date": status_date,
            "status_date_missing": status_date is None,
            "current_date": as_date(root, "CurrentDate"),
            "last_saved": as_date(root, "LastSaved"),
            "start": as_date(root, "StartDate"),
            "finish": as_date(root, "FinishDate"),
        },
        "units": units(root),
        "calendars": {
            "default_uid": default_cal,
            "count": len(cals),
            "in_use": cal_mod.summarise(cals, used),
            "definitions": cal_mod.to_dict(cals),
        },
        "prevailing_baseline": prevailing_baseline(tasks),
        # What the organisation keeps in its own fields, discovered rather than
        # assumed: which are populated, what type the values actually are, and a
        # sample -- so a profile interview can show candidates instead of asking
        # someone to recall which field holds the discipline.
        "custom_fields": cf_mod.discover(root),
        "counts": {
            "tasks": len(tasks),
            "leaves": sum(1 for t in tasks if not t["summary"]),
            "summaries": sum(1 for t in tasks if t["summary"]),
            "milestones": sum(1 for t in tasks if t["milestone"]),
            "links": sum(len(t["predecessors"]) for t in tasks),
            "with_physical_percent": sum(
                1 for t in tasks if t["physical_percent_complete"] is not None
            ),
        },
        "tasks": tasks,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("xml", help="MS Project XML export (File > Save As > XML)")
    ap.add_argument("-o", "--out", help="write JSON here instead of stdout")
    args = ap.parse_args()

    model = parse(args.xml)
    blob = json.dumps(model, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(blob + "\n")
        print(
            f"{args.xml}: {model['counts']['tasks']} tasks, "
            f"{model['counts']['links']} links -> {args.out}",
            file=sys.stderr,
        )
    else:
        print(blob)


if __name__ == "__main__":
    main()
