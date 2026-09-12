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


# Two calendars, because a real programme has many and they disagree. The default
# works five 8-hour days; the second works six 9-hour days and carries a holiday.
# A task's duration and span are expressed against ITS calendar, never the header's.
CALENDARS = """  <Calendars>
    <Calendar>
      <UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>
      <BaseCalendarUID>-1</BaseCalendarUID>
      <WeekDays>
        <WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>
        <WeekDay><DayType>2</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>3</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>4</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>5</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>6</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>7</DayType><DayWorking>0</DayWorking></WeekDay>
      </WeekDays>
      <Exceptions/>
    </Calendar>
    <Calendar>
      <UID>2</UID><Name>Earthworks six-day</Name><IsBaseCalendar>1</IsBaseCalendar>
      <BaseCalendarUID>-1</BaseCalendarUID>
      <WeekDays>
        <WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>
        <WeekDay><DayType>2</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>07:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>3</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>07:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>4</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>07:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>5</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>07:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>6</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>07:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
        <WeekDay><DayType>7</DayType><DayWorking>1</DayWorking><WorkingTimes>
          <WorkingTime><FromTime>07:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
        </WorkingTimes></WeekDay>
      </WeekDays>
      <Exceptions>
        <Exception>
          <EnteredByOccurrences>0</EnteredByOccurrences>
          <TimePeriod><FromDate>2026-03-04T00:00:00</FromDate><ToDate>2026-03-04T23:59:00</ToDate></TimePeriod>
          <Occurrences>1</Occurrences><Name>Holiday</Name><Type>1</Type>
          <DayWorking>0</DayWorking>
        </Exception>
      </Exceptions>
    </Calendar>
  </Calendars>
"""


# Custom fields, because an organisation keeps its own meaning in them and the
# discovery step has to be exercised. Aliases deliberately in a mix of languages.
EXT_DEFS = """  <ExtendedAttributes>
    <ExtendedAttribute><FieldID>188743737</FieldID><FieldName>Text3</FieldName>
      <Alias>DISCIPLINA</Alias></ExtendedAttribute>
    <ExtendedAttribute><FieldID>188743746</FieldID><FieldName>Text6</FieldName>
      <Alias>JUSTIFICATIVA</Alias></ExtendedAttribute>
    <ExtendedAttribute><FieldID>188743767</FieldID><FieldName>Number1</FieldName>
      <Alias>QTDE</Alias></ExtendedAttribute>
  </ExtendedAttributes>
"""

DISCIPLINES = ["EARTHWORKS", "DRAINAGE", "PAVEMENT"]


from datetime import datetime, timedelta

SENTINEL = 32768  # what Project writes in a percent block on a non-working day


def _days(start, finish, six_day=False):
    a = datetime.fromisoformat(start).date()
    b = datetime.fromisoformat(finish).date()
    out = []
    cur = a
    while cur <= b:
        working = cur.weekday() < (6 if six_day else 5)
        out.append((cur, working))
        cur += timedelta(days=1)
    return out


def _phasing(kw):
    """Time-phased blocks the way Project writes them: baseline cost per working
    day (type 10) and physical percent per day (type 11, sentinel on non-working
    days). Returns (xml_lines, bcws_at_status)."""
    lines = []
    bl = kw.get("baseline")
    bcws = 0.0
    six = kw.get("cal") == 2
    if bl:
        bstart, bfinish, bcost, _ = bl
        days = [d for d, w in _days(bstart, bfinish, six) if w] or [datetime.fromisoformat(bstart).date()]
        per = bcost / len(days)
        for d in days:
            lines += ["    <TimephasedData>", "      <Type>10</Type>", f"      <UID>{kw['_uid']}</UID>",
                      f"      <Start>{d.isoformat()}T08:00:00</Start>",
                      f"      <Finish>{d.isoformat()}T17:00:00</Finish>",
                      "      <Unit>1</Unit>", f"      <Value>{per:.2f}</Value>", "    </TimephasedData>"]
            if d.isoformat() <= STATUS[:10]:
                bcws += per
    # One empty-valued block, as real exports carry them; it must be skipped.
    if bl:
        lines += ["    <TimephasedData>", "      <Type>10</Type>", f"      <UID>{kw['_uid']}</UID>",
                  f"      <Start>{bl[0]}</Start>", f"      <Finish>{bl[0]}</Finish>",
                  "      <Unit>1</Unit>", "      <Value></Value>", "    </TimephasedData>"]
    phys = kw.get("phys")
    if phys and kw.get("astart"):
        end = kw.get("afinish") or STATUS
        span = _days(kw["astart"], end, six)
        working = [d for d, w in span if w] or [span[0][0]]
        per = phys / len(working)
        for d, w in span:
            lines += ["    <TimephasedData>", "      <Type>11</Type>", f"      <UID>{kw['_uid']}</UID>",
                      f"      <Start>{d.isoformat()}T08:00:00</Start>",
                      f"      <Finish>{d.isoformat()}T17:00:00</Finish>",
                      "      <Unit>2</Unit>",
                      f"      <Value>{per:.4f}</Value>" if w else f"      <Value>{SENTINEL}</Value>",
                      "    </TimephasedData>"]
    return lines, bcws


RESOURCES = """  <Resources>
    <Resource><UID>1</UID><Name>Earthworks cut</Name><Type>0</Type><MaterialLabel>m3</MaterialLabel></Resource>
    <Resource><UID>2</UID><Name>Crew</Name><Type>1</Type></Resource>
  </Resources>
"""

ASSIGNMENTS = []   # collected by task(); emitted by document()


def _iso_hours(q):
    h = int(q)
    m = int(round((q - h) * 60))
    return f"PT{h}H{m}M0S"


def _assignment(uid, task_uid, rid, planned, executed, remaining, astart, afinish, daily):
    lines = ["  <Assignment>", f"    <UID>{uid}</UID>", f"    <TaskUID>{task_uid}</TaskUID>",
             f"    <ResourceUID>{rid}</ResourceUID>", f"    <Units>{planned}</Units>",
             f"    <Work>{_iso_hours(planned)}</Work>",
             f"    <ActualWork>{_iso_hours(executed)}</ActualWork>",
             f"    <RemainingWork>{_iso_hours(remaining)}</RemainingWork>"]
    if astart:
        lines.append(f"    <ActualStart>{astart}</ActualStart>")
    if afinish:
        lines.append(f"    <ActualFinish>{afinish}</ActualFinish>")
    lines += ["    <Baseline>", "      <Number>1</Number>",
              f"      <Work>{_iso_hours(planned)}</Work>", "    </Baseline>"]
    for day, q in daily:
        lines += ["    <TimephasedData>", "      <Type>2</Type>", f"      <UID>{uid}</UID>",
                  f"      <Start>{day}T08:00:00</Start>", f"      <Finish>{day}T17:00:00</Finish>",
                  "      <Unit>2</Unit>", f"      <Value>{_iso_hours(q)}</Value>", "    </TimephasedData>"]
    lines.append("  </Assignment>")
    return "\n".join(lines)


def task(uid, tid, name, **kw):
    kw["_uid"] = uid
    if kw.get("material"):
        planned, executed, daily = kw["material"]
        remaining = max(0.0, planned - executed)
        ASSIGNMENTS.append(_assignment(1000 + uid, uid, 1, planned, executed, remaining,
                                       kw.get("astart"), kw.get("afinish"), daily))
    if kw.get("unassigned"):
        ASSIGNMENTS.append(_assignment(2000 + uid, uid, -1, 0, 0, 0, None, None, []))
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
        f"    <CalendarUID>{kw.get('cal', -1)}</CalendarUID>",
    ]
    if kw.get("constraint") is not None:
        parts.append(f"    <ConstraintType>{kw['constraint']}</ConstraintType>")
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
        if kw.get("finish"):
            lf = datetime.fromisoformat(kw["finish"]) + timedelta(days=int(kw["slack_days"] * 7 / 5))
            parts.append(f"    <LateFinish>{lf.isoformat()}</LateFinish>")
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
    disc = kw.get("disc")
    if disc:
        parts += [
            "    <ExtendedAttribute>",
            "      <FieldID>188743737</FieldID>",
            f"      <Value>{disc}</Value>",
            "    </ExtendedAttribute>",
        ]
    if kw.get("qty") is not None:
        parts += [
            "    <ExtendedAttribute>",
            "      <FieldID>188743767</FieldID>",
            f"      <Value>{kw['qty']}</Value>",
            "    </ExtendedAttribute>",
        ]
    if kw.get("justif"):
        parts += [
            "    <ExtendedAttribute>",
            "      <FieldID>188743746</FieldID>",
            f"      <Value>{kw['justif']}</Value>",
            "    </ExtendedAttribute>",
        ]
    bl = kw.get("baseline")
    phasing_lines, bcws = _phasing(kw)
    parts += phasing_lines
    if bl:
        parts.append(f"    <BCWS>{bcws:.2f}</BCWS>")
    if bl and kw.get("phys") is not None:
        bstart, bfinish, bcost, bhours = bl
        bcwp = kw["bcwp_override"] if "bcwp_override" in kw else bcost * kw["phys"] / 100.0
        parts.append(f"    <BCWP>{bcwp:.2f}</BCWP>")
        parts.append("    <EarnedValueMethod>1</EarnedValueMethod>")
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
        "  <DefaultTaskEVMethod>1</DefaultTaskEVMethod>\n"
        f"  <CurrentDate>{STATUS}</CurrentDate>\n"
        f"  <MinutesPerDay>{MPD}</MinutesPerDay>\n"
        "  <MinutesPerWeek>2400</MinutesPerWeek>\n"
        "  <DaysPerMonth>20</DaysPerMonth>\n"
        "  <CalendarUID>1</CalendarUID>\n"
        + CALENDARS + EXT_DEFS +
        "  <Tasks>\n" + "\n".join(tasks) + "\n  </Tasks>\n"
        + RESOURCES +
        "  <Assignments>\n" + "\n".join(ASSIGNMENTS) + "\n  </Assignments>\n"
        "</Project>\n"
    )


# A consistent five-day working window used wherever nothing should be flagged.
WIN = dict(start="2026-03-02T08:00:00", finish="2026-03-06T17:00:00", dur_hours=40)
BL_OK = ("2026-03-02T08:00:00", "2026-03-06T17:00:00", 10000.0, 40)


def _decorate(tasks):
    """Spread a closed-set discipline and a numeric quantity across the tasks.

    Only one task carries a justification, so the discovery step has both a good
    grouping candidate and a barely-populated field whose emptiness is the finding.
    """
    out = []
    for i, raw in enumerate(tasks):
        disc = DISCIPLINES[i % len(DISCIPLINES)]
        extra = [
            "    <ExtendedAttribute>",
            "      <FieldID>188743737</FieldID>",
            f"      <Value>{disc}</Value>",
            "    </ExtendedAttribute>",
            "    <ExtendedAttribute>",
            "      <FieldID>188743767</FieldID>",
            f"      <Value>{(i + 1) * 10}</Value>",
            "    </ExtendedAttribute>",
        ]
        if i == 0:
            extra += [
                "    <ExtendedAttribute>",
                "      <FieldID>188743746</FieldID>",
                "      <Value>Weather</Value>",
                "    </ExtendedAttribute>",
            ]
        out.append(raw.replace("\n  </Task>", "\n" + "\n".join(extra) + "\n  </Task>"))
    return out


def positive():
    ASSIGNMENTS.clear()
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
    # On the six-day calendar, whose day is 9 hours and which loses 4 March to a
    # holiday. Duration matches the real working time, so this must NOT raise G --
    # it is the negative control for the calendar path.
    t.append(task(13, 13, "Six-day calendar, consistent", cal=2,
                  start="2026-03-02T07:00:00", finish="2026-03-06T17:00:00",
                  dur_hours=36, astart="2026-03-02T07:00:00", pct=50,
                  baseline=("2026-03-02T07:00:00", "2026-03-06T17:00:00", 12000.0, 36)))
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
    # --- Productivity: quantities as hours of the ISO duration ---
    # 22: in progress, 1,200 m3 planned, 400 executed in 8 working days -> 50/day own
    # rate; baseline finish 30/06, trend finish 03/07, late finish via slack.
    t.append(task(22, 22, "Cut in progress", start="2026-06-17T08:00:00",
                  finish="2026-07-03T17:00:00", dur_hours=96, astart="2026-06-17T08:00:00",
                  pct=33, phys=33, slack_days=20,
                  baseline=("2026-06-17T08:00:00", "2026-06-30T17:00:00", 24000.0, 80),
                  material=(1200.0, 400.0, [(f"2026-06-{d:02d}", 50.0) for d in (17,18,19,22,23,24,25,26)])))
    # 23: complete, 800 m3 in 4 working days -> 200/day, lifts the global rate.
    t.append(task(23, 23, "Cut complete", start="2026-06-01T08:00:00",
                  finish="2026-06-04T17:00:00", dur_hours=32, astart="2026-06-01T08:00:00",
                  afinish="2026-06-04T17:00:00", pct=100, phys=100,
                  baseline=("2026-06-01T08:00:00", "2026-06-04T17:00:00", 16000.0, 32),
                  material=(800.0, 800.0, [(f"2026-06-{d:02d}", 200.0) for d in (1,2,3,4)])))
    # 24: physical percent reported, no executed quantity entered -> inferred.
    t.append(task(24, 24, "Cut with percent only", start="2026-06-22T08:00:00",
                  finish="2026-07-10T17:00:00", dur_hours=120, astart="2026-06-22T08:00:00",
                  pct=25, phys=25, slack_days=5,
                  baseline=("2026-06-22T08:00:00", "2026-07-10T17:00:00", 30000.0, 120),
                  material=(1500.0, 0.0, [])))
    # 25: no resource at all, the -1 assignment the tool writes.
    t.append(task(25, 25, "No resource", **WIN, baseline=BL_OK, unassigned=True))

    # --- Network quality ---
    # 26: pinned by a must-finish-on constraint (type 3), incomplete.
    t.append(task(26, 26, "Pinned by MFO", start="2026-07-13T08:00:00",
                  finish="2026-07-17T17:00:00", dur_hours=40, constraint=3,
                  baseline=("2026-07-13T08:00:00", "2026-07-17T17:00:00", 5000.0, 40)))
    # 27: follows 26 with a 3-day lag (positive), so Q3 has a case; no successor.
    t.append(task(27, 27, "After a lag", start="2026-07-23T08:00:00",
                  finish="2026-07-29T17:00:00", dur_hours=40,
                  baseline=("2026-07-23T08:00:00", "2026-07-29T17:00:00", 5000.0, 40),
                  preds=[(26, 1, 3)]))
    # 28: a SUMMARY carrying a link, which logic should never do.
    t.append(task(28, 28, "Summary with a link", summary=True, level=1,
                  start="2026-07-13T08:00:00", finish="2026-07-29T17:00:00", dur_hours=120,
                  preds=[(1, 1, 0)]))

    # --- New network rules, each with its own control ---
    # 14 -> 15: FS with a 2-day LEAD (negative lag). The predecessor finished one
    # working day after the successor started, which the lead allows. Must NOT be A1.
    t.append(task(14, 14, "Lead predecessor", **WIN,
                  astart="2026-03-02T08:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, baseline=BL_OK))
    t.append(task(15, 15, "Successor within the lead", start="2026-03-05T08:00:00",
                  finish="2026-03-11T17:00:00", dur_hours=40,
                  astart="2026-03-05T08:00:00", pct=30,
                  baseline=("2026-03-05T08:00:00", "2026-03-11T17:00:00", 10000.0, 40),
                  preds=[(14, 1, -2)]))
    # 16 -> 17: both complete, order inverted. By decision this leaves the count
    # and is recorded as ignored, for the forensics.
    t.append(task(16, 16, "Both complete, predecessor", **WIN,
                  astart="2026-03-03T08:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, baseline=BL_OK))
    t.append(task(17, 17, "Both complete, successor started first", **WIN,
                  astart="2026-03-02T08:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, baseline=BL_OK, preds=[(16, 1, 0)]))
    # 18 -> 19: SS with 3 days lag; successor started only 1 day after. Must be A1.
    t.append(task(18, 18, "SS predecessor", **WIN,
                  astart="2026-03-02T08:00:00", pct=40, baseline=BL_OK))
    t.append(task(19, 19, "SS successor too early", start="2026-03-03T08:00:00",
                  finish="2026-03-09T17:00:00", dur_hours=40,
                  astart="2026-03-03T08:00:00", pct=10,
                  baseline=("2026-03-03T08:00:00", "2026-03-09T17:00:00", 10000.0, 40),
                  preds=[(18, 3, 3)]))
    # 20: start in the past with no actual start (and a future finish) -> H by the
    # start condition, not the finish one.
    t.append(task(20, 20, "H start elapsed", start="2026-06-22T08:00:00",
                  finish="2026-07-10T17:00:00", dur_hours=120,
                  baseline=("2026-06-22T08:00:00", "2026-07-10T17:00:00", 10000.0, 120)))
    # 21: a COSTED milestone at 100%. The tool writes zero earned value for it; the
    # method counts its cost. Reconciliation must classify this, not hide it.
    # Executed in March, but its BASELINE sits in November, after the status date.
    # The tool credits earned value only inside the baseline window up to the
    # status date, so it writes zero here while the method credits the cost.
    t.append(task(21, 21, "Done ahead of its baseline window", milestone=True,
                  start="2026-03-06T17:00:00", finish="2026-03-06T17:00:00",
                  dur_hours=0, astart="2026-03-06T17:00:00", afinish="2026-03-06T17:00:00",
                  pct=100, phys=100, bcwp_override=0.0,
                  baseline=("2026-11-25T14:00:00", "2026-11-30T11:00:00", 2500.0, 16)))

    # The migration rule: task 11 is a predecessor of 12, and 12 has started.
    # That is NOT an A1 breach -- 11 is a record defect and already sits in P.
    t.append(task(12, 12, "P successor must not raise A1", **WIN,
                  astart="2026-03-04T08:00:00", pct=20, baseline=BL_OK,
                  preds=[(11, 1, 0)]))
    return document("Positive fixture", _decorate(t))


def negative():
    """A consistent schedule. Every check must stay silent on this file."""
    ASSIGNMENTS.clear()
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
    return document("Negative fixture", _decorate(t))


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
    ASSIGNMENTS.clear()
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
    return document(f"Cycle fixture {which}", _decorate(t))


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
