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
| A1 | Execution out of sequence: a successor is running against what its link allows |
| A2 | Total inversion: successor complete, predecessor never started |

**What A1 evaluates, exactly.** All four relationship types, on actual dates, on the
successor's calendar, honouring the lag:

- **Finish-to-start.** The successor has started and is not finished. Breach if the predecessor
  has no actual finish, or if it finished after the successor started by more than the lead
  allows. A link with a negative lag is an intentional overlap, and accusing it is a false
  positive that an in-tool implementation measured as the first thing it would do differently.
- **Start-to-start.** Both started: breach if the successor started before the lag allowed.
  Successor started and predecessor never did: breach.
- **Finish-to-finish** and **start-to-finish**: the same shape, on the corresponding ends.
- **Pairs with both activities complete leave the count, by decision.** They no longer change a
  forecast. They are recorded under `ignored` in the data file, with the overlap in days,
  because a history of out-of-sequence execution is evidence for the forensics.

**Both ends of a violated link are marked**, and the report counts three defensible ways:
distinct activities, as successors, as predecessors. Align with whatever the other party's
tool shows.

**The relationship types evaluated are declared** in the output, with counts. Silence about
start-to-start links looks like coverage; it is not.

## Layer 2 — Date adherence

| Code | Finding |
|---|---|
| H | A trend date elapsed with nothing behind it: start with no actual start, or finish with no actual finish |
| E | Pulled forward by 30 working days or more, on the activity's own calendar, and never started |
| C | Delayed by 30 working days or more, on the activity's own calendar |

**The threshold is in working days of the activity's calendar**, not calendar days, so that
the count agrees with what an in-tool check shows in the meeting. Calendar days are reported
alongside. **Completed activities stay in C on purpose**: consumed delay is information.

**H refuses to run without a status date.** Defaulting to today would change the answer every
day the review is re-run, silently.

## Layer 3 — Reporting consistency

| Code | Finding |
|---|---|
| G | Duration disagrees with the start-to-finish window — *a thermometer, not an independent finding* |
| P | Pending record: 100% physical with no actual finish |
| B | Milestones with no deadline set |
| F | In progress with percent complete at zero — *duration-based percent, deliberately; the physical figure belongs to P* |

**F is standby-grade.** On a schedule reported by physical progress it collides with the
reporting flow and fires on activities that are fine. It is shown with the "check" severity,
never counted as a finding on its own.

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

## The codes are stable identifiers

A finding keeps its code when the implementation changes. Without that you cannot discuss a
problem across weeks, or hand the discussion to somebody else.

Six checks are the working set: **A1, A2, H, E, C, G**. Two more, **B** and **F**, are worth
running but are often already covered by whatever else an organisation reviews, so they are
opt-in. **P** is not a check so much as a rule that reshapes A1 and A2.

Two checks were deliberately dropped from an earlier, longer set — *leaf with no successor* and
*deviation with no justification filled* — because another analysis already in use covered them.
**Removing a check matters as much as adding one:** a set that only grows becomes noise and
stops being run.

### Before inventing a code scheme, look for the one that already exists

A longer twelve-check numbering existed earlier in this method's history and is superseded. It
is worth one table, purely as a warning, because it **collides dangerously** with the working
set:

| Code | In the superseded set | In the working set |
|---|---|---|
| A1 | Start elapsed with no progress | Successor started without predecessor complete |
| A2 | Finish elapsed with no progress | Total inversion |
| I1 / I1b / I2 | the network findings | *(these are A1 and A2 now)* |

**The same prefix, the same shape, different meanings.** Two people can leave a meeting agreeing
about different things, with no conflict and no symptom. A second scheme with the same shape is
worse than no scheme at all — without codes, people describe the finding and make themselves
understood.

The same defect appears in miniature wherever an internal name and a displayed name drift apart:
one gets renamed and the other does not, and nobody decides it, it just happens. Check which one
somebody is quoting before answering them.

## Two ways this gets run, and only one of them is this skill

**Inside the scheduling tool, in its macro language.** This is the strongest form: no export, no
conversion, nothing to install, and the result is navigable in the schedule itself with each
activity in its own context — which is what lets you walk through a finding with the other party
in the meeting. A check that needs preparation does not get run weekly; one that is a keystroke
does. The pattern that transfers: **mark the flagged activities in a spare flag field and apply a
filter**, rather than producing a list beside the schedule; change nothing but the marker and the
display; and ship a routine that clears the markers, because a tool that dirties somebody else's
file must know how to undo. Two limits worth knowing before you plan such a tool: the macro can
usually create its own tables, but some tools do not allow *creating* groupings by macro, only
applying them — so groupings stay a one-time manual setup.

Implementations of this exist as proprietary products and are not part of this skill.

**Here, from an exported file.** This is what the skill does, and what `references/usage.md`
describes: the scheduling tool exports its own documented XML, and the bundled scripts read it,
run the checks and write a report. It needs nothing installed beyond Python, it runs on any
platform, and it works on a file somebody emailed you without opening their tool at all.

The trade is real and worth stating: you lose the in-context navigation, and you gain
portability, a machine-readable result, and a report you can diff against last month's.

## Minimum inputs

A **status date** — every adherence check is measured against it, and defaulting to today would
silently change the answer each day the review is re-run. A **saved baseline** for anything that
compares against plan. And populated fields for the checks that read them: a field left empty is
itself a reportable finding, not a reason to skip the check.

## What the sweep buys

On the in-tool implementation: a schedule of 5,251 activities reviewed in under 30 seconds against
roughly three hours by hand (`reported`; the manual figure is a practice estimate, not timed).

The larger gain is not speed. **The sweep becomes exhaustive by construction.** Manual analysis
carries coverage risk, and coverage risk is invisible — you cannot see the activity you did not
look at.

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
