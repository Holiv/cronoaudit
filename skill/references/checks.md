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

`measured` — read from the deployed macro source and its operating notes.

**The canonical set is the one above, and it is also what the deployed tool runs today.** An
earlier version of this document claimed the deployed automation used a different numbering
and gave a mapping table for it. That was wrong: the two converged. Six checks are active and
two are on standby.

| Code | Status | Routine name in the tool | Card label in the report |
|---|---|---|---|
| A1 | active | `..._A_ForaDeSequencia` | A1 |
| A2 | active | `..._A_InversaoTotal` | A2 |
| H | active | `..._H_VencidasSemRealizacao` | H |
| E | active | `..._B2_AntecipadaNaoIniciada` | E |
| C | active | `..._C1_Atrasada30d` | C |
| G | active | `..._G_DuracaoXJanela` | G |
| B | standby | `..._B_MarcosSemDataLimite` | — |
| F | standby | `..._F_PctConcluidaZerada` | — |
| P | transversal rule | `EhApontPendente` | — |

**One residual mismatch, internal to the tool:** the routine names still carry the legacy
`B2` and `C1` while the report cards show `E` and `C`. Same check, two names, depending on
whether you are reading the macro menu or the report. Worth knowing before someone quotes a
code from one and looks for it in the other.

### The superseded numbering, and why it is worth recording

An earlier twelve-check numbering existed and is **superseded**. It matters only because it
**collides dangerously** with the canonical set:

| Code | In the superseded set | In the canonical set |
|---|---|---|
| A1 | Start elapsed with no progress | Successor started without predecessor complete |
| A2 | Finish elapsed with no progress | Total inversion |
| I1 / I1b / I2 | the network findings | *(these are A1 and A2 now)* |

**The same prefix, the same shape, different meanings.** Two parties can leave a meeting
agreeing about different things, with no conflict and no symptom.

Two checks left the model deliberately when the set converged — *leaf with no successor* and
*deviation with no justification filled* — because another analysis already in use covered
them. **Removing a check matters as much as adding one:** a set that only grows becomes noise
and stops being run.

The transferable rule: **before inventing a code scheme, look for the one that already
exists.** A second scheme with the same shape is worse than no scheme at all — without codes,
people describe the finding and make themselves understood.

## How a review actually gets run

`measured` from the tool's operating notes. This is the operating half of the method, and it
is what makes the difference between a documented method and a used one.

**Where it runs: inside the scheduling tool, in its macro language.** No export, no
conversion, no pipeline, nothing to install. Whoever receives the file runs it on the file.
**A check that needs preparation does not get run weekly; one that is a keystroke does.**

**Install once.** Import the modules into the tool's global template so they are available in
every file, not just the one open.

**Prepare once.** Create one custom view. The tool's own limit, worth recording rather than
working around: **the macro can create the per-check tables itself, but it cannot create the
groupings — the tool only allows applying those, not creating them.** So groupings are a
manual, one-time setup.

**Then, per delivery:**

1. **Work on a copy of the delivered file.** The macros write only a marker field and the
   display, never schedule data — and the instruction is still to use a copy.
2. **Run the network checks first** (A1, A2). The ordering rationale is in `SKILL.md` and it
   is not a preference.
3. **Investigate finding by finding.** Each check marks the activities in one spare flag
   field and applies a filter, rather than producing a separate list. **The result is
   navigable inside the schedule, with the activity in its context** — which is what lets you
   walk through it with the other party in the meeting.
4. **Apply a grouping** to see the finding by discipline, by float band, or by calendar.
5. **Generate the report with one command.** It applies the same criteria, injects them into a
   template and opens a full HTML report in the browser: weighted progress, a card per
   finding, distribution charts, the full list of flagged activities per finding, and a
   print-to-PDF button. There is a secondary routine that exports the same base to a
   spreadsheet, with the per-activity markings and stable identifiers, for whoever prefers to
   work there.
6. **Clear the markings when done.** A routine removes the flags and restores the default
   view. **A tool that dirties somebody else's file must know how to undo.**

**Minimum inputs.** A status date, and a saved baseline for anything that compares against
plan. Checks that read a justification field need that field populated — and its being empty
is itself a reportable finding.

**What it buys, measured:** a schedule of 5,251 activities reviewed in under 30 seconds
against roughly three hours by hand (the manual figure is his practice estimate, not
timed). The larger gain is not speed: **the sweep becomes exhaustive by construction.** Manual
analysis carries coverage risk, and coverage risk is invisible — you cannot see the activity
you did not look at.

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
