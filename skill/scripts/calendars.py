#!/usr/bin/env python3
"""Calendars, read from the file rather than assumed.

This module exists because of a measured mistake. A first version of the checks
counted Monday to Friday and divided durations by the project header's
minutes-per-day. On a real programme that produced 1,412 flagged activities, 27%
of the schedule, with a median disagreement of two days: almost all of it holidays
and differing shift lengths, drowning the 64 activities that disagreed by more
than sixty days.

The schedule had 107 calendars. The default worked 8 hours; the earthworks calendar
worked 9; a rainy-season calendar carried 202 exceptions. Only 266 of 6,484 tasks
were on the default. **Every duration, variance and span in the file is expressed
against the calendar of its own task**, and that calendar is where a construction
schedule keeps its holidays and its weather reserve. Leaving it out does not
approximate the answer; it invents one.

It is the same rule as reading minutes-per-day from the file: never assume the
conversion basis. And it is why a calendar registered against the wrong year embeds
optimism that nothing in the file announces -- the month gets its full working days
instead of its real ones.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta

NS = {"p": "http://schemas.microsoft.com/project"}

# MSPDI numbers weekdays from Sunday. Python's weekday() starts at Monday.
_PY_TO_MSPDI = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 1}


def _text(node, tag):
    if node is None:
        return None
    el = node.find(f"p:{tag}", NS)
    return el.text.strip() if el is not None and el.text else None


def _intervals_of(working_times) -> list:
    """A WorkingTimes block as minute-of-day intervals.

    Intervals, not a daily total. A task can start and finish mid-shift, and the
    only correct way to compare a duration against its window is to add up the
    working time actually inside that window -- which needs to know when the shift
    runs, not just how long it is.
    """
    if working_times is None:
        return []
    out = []
    for wt in working_times.findall("p:WorkingTime", NS):
        fr, to = _text(wt, "FromTime"), _text(wt, "ToTime")
        if not fr or not to:
            continue
        try:
            a = datetime.strptime(fr[:8], "%H:%M:%S")
            b = datetime.strptime(to[:8], "%H:%M:%S")
        except ValueError:
            continue
        start = a.hour * 60 + a.minute + a.second / 60.0
        end = b.hour * 60 + b.minute + b.second / 60.0
        if end <= start:  # crosses midnight, e.g. a night shift
            out.append((start, 1440.0))
            if end > 0:
                out.append((0.0, end))
        else:
            out.append((start, end))
    out.sort()
    return out


def _span(intervals) -> float:
    return sum(b - a for a, b in intervals)


def _as_date(raw):
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


class Calendar:
    """One calendar: a working week plus dated exceptions."""

    __slots__ = ("uid", "name", "base_uid", "weekday_intervals", "exception_intervals",
                 "_day_minutes", "_prefix", "_origin")

    def __init__(self, uid, name, base_uid):
        self.uid = uid
        self.name = name
        self.base_uid = base_uid
        self.weekday_intervals: dict[int, list] = {}
        self.exception_intervals: dict[date, list] = {}
        self._day_minutes = None
        self._prefix = None
        self._origin = None

    @property
    def day_minutes(self) -> float:
        """The standard working day for THIS calendar, not the project's.

        The most common non-zero weekday length. An 8-hour default and a 9-hour
        earthworks shift convert the same duration into different day counts, and
        using the wrong one is the single largest source of false findings.
        """
        if self._day_minutes is None:
            vals = [_span(v) for v in self.weekday_intervals.values() if _span(v) > 0]
            self._day_minutes = Counter(vals).most_common(1)[0][0] if vals else 480.0
        return self._day_minutes

    def intervals_on(self, day: date) -> list:
        """Working intervals on one date: an exception overrides the working week."""
        if day in self.exception_intervals:
            return self.exception_intervals[day]
        return self.weekday_intervals.get(_PY_TO_MSPDI[day.weekday()], [])

    def minutes_on(self, day: date) -> float:
        return _span(self.intervals_on(day))

    def working_minutes(self, start, finish) -> float | None:
        """Working minutes between two instants, on this calendar.

        Partial first and last days are handled, which is the whole point: a task
        starting at 14:55 and finishing at 14:48 four days later does not occupy
        four working days, and comparing its duration against a whole-day count
        manufactures a finding on every such task. Measured: that mistake flagged
        2,049 activities on one real programme, every one of them correct.
        """
        if start is None or finish is None:
            return None
        if finish < start:
            start, finish = finish, start
        total = 0.0
        day = start.date()
        last = finish.date()
        while day <= last:
            lo = (start.hour * 60 + start.minute + start.second / 60.0) if day == start.date() else 0.0
            hi = (finish.hour * 60 + finish.minute + finish.second / 60.0) if day == last else 1440.0
            for a, b in self.intervals_on(day):
                total += max(0.0, min(b, hi) - max(a, lo))
            day += timedelta(days=1)
        return total

    def is_working(self, day: date) -> bool:
        return self.minutes_on(day) > 0

    def _build(self, lo: date, hi: date) -> None:
        """Prefix-sum the working days across the range, so spans cost O(1)."""
        self._origin = lo
        n = (hi - lo).days + 2
        prefix = [0] * n
        cur = lo
        for i in range(1, n):
            prefix[i] = prefix[i - 1] + (1 if self.is_working(cur) else 0)
            cur += timedelta(days=1)
        self._prefix = prefix

    def working_days(self, start, finish, lo=None, hi=None) -> int | None:
        """Working days in [start, finish] inclusive, by this calendar."""
        if start is None or finish is None:
            return None
        a, b = start.date() if isinstance(start, datetime) else start, \
            finish.date() if isinstance(finish, datetime) else finish
        if b < a:
            a, b = b, a
            sign = -1
        else:
            sign = 1
        if self._prefix is None or lo is None:
            count = 0
            cur = a
            while cur <= b:
                if self.is_working(cur):
                    count += 1
                cur += timedelta(days=1)
            return sign * count
        if a < self._origin or b > self._origin + timedelta(days=len(self._prefix) - 2):
            count = 0
            cur = a
            while cur <= b:
                if self.is_working(cur):
                    count += 1
                cur += timedelta(days=1)
            return sign * count
        i = (a - self._origin).days
        j = (b - self._origin).days + 1
        return sign * (self._prefix[j] - self._prefix[i])


def parse_calendars(root) -> dict:
    """Read every calendar, then resolve inheritance from base calendars."""
    cals: dict[str, Calendar] = {}
    for el in root.findall("p:Calendars/p:Calendar", NS):
        uid = _text(el, "UID")
        if uid is None:
            continue
        cal = Calendar(uid, _text(el, "Name") or uid, _text(el, "BaseCalendarUID"))

        weekdays = el.find("p:WeekDays", NS)
        if weekdays is not None:
            for wd in weekdays.findall("p:WeekDay", NS):
                day_type = _text(wd, "DayType")
                working = _text(wd, "DayWorking") == "1"
                times = wd.find("p:WorkingTimes", NS)
                if day_type == "0":
                    # Older files express exceptions as a WeekDay with a TimePeriod.
                    period = wd.find("p:TimePeriod", NS)
                    frm, to = _as_date(_text(period, "FromDate")), _as_date(_text(period, "ToDate"))
                    if frm:
                        ivs = _intervals_of(times) if working else []
                        cur, last = frm, to or frm
                        while cur <= last:
                            cal.exception_intervals[cur] = ivs
                            cur += timedelta(days=1)
                elif day_type and day_type.isdigit():
                    cal.weekday_intervals[int(day_type)] = _intervals_of(times) if working else []

        exceptions = el.find("p:Exceptions", NS)
        if exceptions is not None:
            for ex in exceptions.findall("p:Exception", NS):
                period = ex.find("p:TimePeriod", NS)
                frm, to = _as_date(_text(period, "FromDate")), _as_date(_text(period, "ToDate"))
                if not frm:
                    continue
                working = _text(ex, "DayWorking") == "1"
                ivs = _intervals_of(ex.find("p:WorkingTimes", NS)) if working else []
                # A working exception with no explicit times keeps the week's hours.
                inherit = working and not ivs
                cur, last = frm, to or frm
                while cur <= last:
                    cal.exception_intervals[cur] = (
                        cal.weekday_intervals.get(_PY_TO_MSPDI[cur.weekday()], [])
                        if inherit else ivs
                    )
                    cur += timedelta(days=1)
        cals[uid] = cal

    # Inheritance: a calendar with no working week of its own takes its base's.
    for cal in cals.values():
        seen = set()
        base = cal.base_uid
        while (not cal.weekday_intervals) and base and base in cals and base not in seen:
            seen.add(base)
            parent = cals[base]
            cal.weekday_intervals = {k: list(v) for k, v in parent.weekday_intervals.items()}
            for day, ivs in parent.exception_intervals.items():
                cal.exception_intervals.setdefault(day, ivs)
            base = parent.base_uid
    return cals


def summarise(cals: dict, task_counts: Counter) -> list:
    """A reportable view: which calendars carry the work, and how they differ."""
    rows = []
    for uid, cal in cals.items():
        used = task_counts.get(uid, 0)
        if not used:
            continue
        working_week = sum(1 for d in range(1, 8) if _span(cal.weekday_intervals.get(d, [])) > 0)
        non_working_exceptions = sum(1 for ivs in cal.exception_intervals.values() if not ivs)
        rows.append({
            "uid": uid,
            "name": cal.name,
            "tasks": used,
            "hours_per_day": round(cal.day_minutes / 60.0, 2),
            "working_days_per_week": working_week,
            "exceptions": len(cal.exception_intervals),
            "non_working_exceptions": non_working_exceptions,
        })
    rows.sort(key=lambda r: r["tasks"], reverse=True)
    return rows


def prepare(cals: dict, lo: date, hi: date) -> None:
    """Precompute the working-day index over the range the schedule spans."""
    for cal in cals.values():
        cal._build(lo, hi)


def to_dict(cals: dict) -> dict:
    """Serialise calendars so a later stage works from the JSON model alone.

    The pipeline stays JSON-in, JSON-out: parse once, then every consumer reads the
    same model. Calendars have to travel with it, because without them a duration
    cannot be converted and a span cannot be counted.
    """
    return {
        uid: {
            "name": cal.name,
            "base_uid": cal.base_uid,
            "day_minutes": cal.day_minutes,
            "weekday_intervals": {str(k): v for k, v in cal.weekday_intervals.items()},
            "exception_intervals": {
                d.isoformat(): ivs for d, ivs in sorted(cal.exception_intervals.items())
            },
        }
        for uid, cal in cals.items()
    }


def from_dict(blob: dict) -> dict:
    """Rebuild calendars from a serialised model."""
    out = {}
    for uid, d in (blob or {}).items():
        cal = Calendar(uid, d.get("name") or uid, d.get("base_uid"))
        cal.weekday_intervals = {
            int(k): [tuple(x) for x in v] for k, v in (d.get("weekday_intervals") or {}).items()
        }
        cal.exception_intervals = {
            _as_date(k): [tuple(x) for x in v]
            for k, v in (d.get("exception_intervals") or {}).items() if _as_date(k)
        }
        if d.get("day_minutes"):
            cal._day_minutes = float(d["day_minutes"])
        out[uid] = cal
    return out


def resolve(cals: dict, uid, default_uid=None):
    """The calendar governing a task, falling back to the project default."""
    if uid and uid in cals:
        return cals[uid]
    if default_uid and default_uid in cals:
        return cals[default_uid]
    return None
