# The check catalogue

Stable codes. A finding keeps its code when the implementation changes — that is what
lets you discuss the same problem across weeks and across revisions of the tool.

Provenance: the set originated in a manual critical analysis of a real delivered
schedule, then was consolidated into automation. **No check was invented for
completeness** — each one came from a problem actually found. That is why the list is
short and every item has an owner. Removing a check matters as much as adding one: a set
that only grows becomes noise and stops being run.

## Layer 1 — Network integrity

Run first. See the ordering rationale in `SKILL.md`.

| Code | Finding |
|---|---|
| A1 | Successor started without the predecessor complete |
| A2 | Total inversion: successor complete, predecessor not even started |

A2 is the extreme of A1 and deserves its own code because it is unanswerable in a
meeting. A measured instance: an activity complete while its predecessor still forecast
finishing nearly a year later.

**Mark both ends of a violated link, not just the successor.** This is a presentation
decision, not a criterion change — but it changes the displayed count, so decide which
convention is official and say so. Align with the tool the other party uses.

## Layer 2 — Date adherence

| Code | Finding |
|---|---|
| H | Trend date elapsed with no actual progress |
| E | Pulled forward by 30 days or more and never started |
| C | Delayed by 30 days or more |

The 30-day threshold is a convention, not a derivation. State it in the report so it can
be argued with. Thresholds compare against variance fields — see the unit trap in
`reading-schedules.md` before writing the comparison.

## Layer 3 — Reporting consistency

| Code | Finding |
|---|---|
| G | Duration disagrees with the start-to-finish window — *a thermometer, not an independent finding* |
| P | Pending record: 100% physical with no actual finish |
| B | Milestones with no deadline set |
| F | In progress with percent complete at zero |

**G is a thermometer.** It flags that something was edited inconsistently; it does not by
itself say what. Treat it as a pointer to inspect, never as a finding to report on its
own.

**P carries the transversal rule.** A predecessor in the P condition **does not count as
a network breach** — it migrates to P. Without this, a record-keeping problem is reported
as an execution problem.

**B is quiet and expensive.** With no deadline set, milestones display comfortable float
even when a contractual milestone has elapsed unachieved. A measured delivery had zero of
its activities with a deadline populated. Note the distinction: **a deadline is not a
constraint** — it does not move dates, it only reveals slippage. Its absence hides the
slippage rather than causing it.

## Which code set is canonical

Two numberings exist for the same findings, and the skill's own principle — codes are
stable identifiers — only holds if you say which one governs.

**The generic set above (A1, A2, H, E, C, G, P, B, F) is canonical for this method.** The
deployed in-tool automation grew a different numbering first, and it is still what appears
on screen in a meeting. Map before you speak:

| Generic (canonical) | Deployed automation | Finding |
|---|---|---|
| A1 | I1 / I1b | Successor started without predecessor complete (either end of the link) |
| A2 | I2 | Total inversion |
| H | A1, A2 | Trend date elapsed with no actual progress (start, finish) |
| E | B2 | Pulled forward 30+ days, never started |
| C | C1 | Delayed 30+ days |
| G | H1 | Duration disagrees with the start-to-finish window |
| F | E1 | In progress with percent complete at zero |
| P | — | Pending record: 100% physical, no actual finish (added after the first set) |
| B | — | Milestone with no deadline set |
| — | D1 | Deviation with no justification filled |
| — | D2 | Regulator-deviation threshold |

Note the collision trap: **A1 and A2 mean different things in the two sets.** In the
generic set they are network findings; in the deployed numbering they are elapsed-date
findings, and the network ones are the I codes. Never quote a bare code across the two
without naming which set.

D1 and D2 left the deployed model as already covered by another analysis in use, and are
not in the generic set. Removing a check matters as much as adding one.

## Findings not in the set, but worth checking

These were measured and are real; they were not promoted to coded checks because they need
inputs beyond the schedule file, or they were covered by another analysis in use.

- **Calendar applied to the wrong year.** Productivity reserve registered against one year
  while the activities execute in another: the month gets its full working days instead of
  its real ones. Measured optimism on the order of 30% in duration, with nothing in the
  file indicating it. The affected activities were in the start-up of the highest-weight
  section, which is where it costs most.
- **Out-of-sequence execution contaminating trend dates.** This is the consequence of A1
  and A2, and the reason they run first.
- **Inconsistent record-keeping as a finding class**, of which P is the one instance that
  earned a code.
- **Justification / delay reason left blank.** A measured delivery had it empty in every
  single activity. Worth reporting as a contract-compliance finding rather than a schedule
  one.
- **Three different dates get confused:** the status date, the meeting date, and the date
  the file was saved. Always state which one a figure is measured at.

## Validation of the set

Applied in the field on a road-concession programme, on schedules delivered by
third-party contractors. On one delivery of 510 activities:

| | |
|---|---|
| Violated finish-to-start links at the status date | 60 |
| Distinct activities involved | 77 |
| Of those, in total inversion | 8 |
| Pulled forward and never started | 43 |
| In progress with percent complete at zero | 31 |
| Activities with a deadline set | 0 of 510 |
| Activities with justification filled | 0 of 510 |

The aggregate that made the case for weight distribution: **+3.72 percentage points of
apparent advance** which, read row by row, was 51 out-of-sequence activities covering 15
with negative deviation, six of which should have been complete and sat at zero. The two
sections carrying the large majority of baseline cost were at 0.0% planned and 0.0%
actual. There was no advance where the money was; there was a failure to start.

Largest file handled in the same programme: 6,483 tasks.
