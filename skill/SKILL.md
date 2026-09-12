---
name: schedule-integrity
description: Review a delivered construction or infrastructure schedule, compare it against the previous version, and audit the progress and earned-value figures derived from it - finding the failures that produce a plausible wrong number rather than an error. Use for schedule critical analysis of a contractor delivery, the periodic cycle report, computing or reconciling earned value (BCWS/BCWP/SPI/CPI), building or debugging an S-curve or physical progress curve, comparing two schedule versions or snapshots, deciding whether a change was execution or a replan, reading a .mpp or MPXJ-parsed schedule programmatically, or explaining why a control indicator disagrees with its source tool. Runs from one command over the schedule tool's own XML export with no dependencies beyond Python, and produces named findings with stable codes, a weighted deviation decomposition, and a self-contained HTML report where every finding carries the filter that reproduces it.
user-invocable: true
---

# Schedule integrity review

A method for auditing a schedule and the indicators derived from it. It targets one
failure class specifically: **the calculation is arithmetically correct, every input is
correct in its own source, the result is plausible, nothing raises an error, and the
number is meaningless.** Textbooks cover how to compute earned value. This covers what
goes wrong silently when you compute it on a real delivered file.

## What this is for, concretely

**Who runs it.** Whoever receives a schedule and has to say whether it is true: the planning
engineer on the contracting side auditing a contractor's delivery, or the contractor's own
planner who wants a delivery that passes. The checks are not traps — they are the questions a
consistent schedule answers by itself.

**The two jobs, and they are different.**

| Job | Question | Input |
|---|---|---|
| **Critical review** (`checks.md`) | Is this delivery internally consistent? | one schedule |
| **Cycle comparison** (`comparing-versions.md`) | What moved since last time, and was it execution or a replan? | two snapshots of the same schedule |

**How you actually run it.** One command, no dependencies beyond Python. Export the schedule
from the tool once (`File > Save As > XML Format`), then:

```
python3 scripts/review.py delivery.xml               # review one delivery
python3 scripts/review.py previous.xml current.xml   # the periodic cycle report
```

Out come a self-contained HTML report with no external references, printable to PDF, and the
same findings as JSON. **The report speaks the schedule's language**, detected from the file's
own text rather than configured, and it says which language it chose and on what evidence. The full process, the flags, the failure messages and the judgement the
tool cannot make for you are in `references/usage.md`. Verify the tool itself with
`python3 scripts/test_checks.py` before trusting a clean result.

**Learning the organisation's own fields.** An organisation keeps its meaning in custom fields:
discipline, work front, contractor, justification, quantity, regulator code. That mapping is the
organisation's asset and cannot be guessed from a schema, but it can be **discovered**. A bundled
step lists every custom field that carries values, with the type inferred from the values rather
than the field name, the fill rate, whether the values form a closed set, and a sample; then it
ranks them by the role they might serve. The report can then group weight by the field you
confirm, named by its alias. **The transferable idea is that the mapping is declared rather than
coded** — one codebase serves organisations that keep their meaning in different places.

Two rules it follows. **Key on the stable field identifier, never on the field name**, because
names arrive translated by the installed language. And **a field that exists and is almost empty
is a finding, not a dimension** — a justification blank on nearly every activity is a
contract-compliance finding waiting to be written down.

**What you must have in hand** before either is worth starting: a status date, a saved
baseline, and for the comparison the previous cycle's file. Fields the checks read must be
populated — and a field left empty is itself a reportable finding, not a reason to skip the
check.

**What comes out.** A report in the structure a mature in-tool analysis proved in meetings:
cover, verdict, tiles, index, views, and one block per finding with problem, impact, solution,
reproduction and the activities collapsed under a toggle. Named findings with stable codes, each one a set of flagged activities
navigable inside the schedule itself rather than a list beside it. A weighted decomposition
that shows where the aggregate deviation actually comes from. A report in which every finding
closes with which columns it came from and which filter reproduces it. And a clean-up routine,
because the file belongs to somebody else.

**What decision it feeds.** Whether to accept the delivery; what to put on the agenda with the
contractor and with what evidence; whether a reported deviation is the works or the reference;
and what the periodic report to management says.

**The questions it answers, in the order they get asked:**

1. Does the logic hold, or is every forecast date in this file derived from a network the works
   does not follow?
2. Which activities are elapsed, pulled forward or delayed beyond tolerance?
3. Is the record-keeping consistent, or am I about to accuse execution of a reporting problem?
4. Where does the aggregate progress figure actually come from, activity by activity?
5. What moved since the last delivery, and was it executed or re-planned?
6. Did the baseline itself move — that is, did my comparison basis change underneath me?
7. Is each indicator's planned half measured against the same reference as its actual half?

**What it does not do.** It does not level resources, run a forensic delay analysis, score a
schedule against the DCMA 14-point assessment, or price anything. It reads and reconciles; it
does not repair the schedule.

## Read this first: the datum question

Before auditing any indicator, ask the question that finds this failure class:

> **Are all the inputs to this calculation measured against the same reference?**

Not *"is the arithmetic right?"* — it is. In surveying, a **datum** is the reference
surface every elevation is measured from. Two elevations can each be perfectly measured
and their difference still be entirely false, if each was surveyed against a different
datum. Nobody miscalculates. The subtraction is correct. The result means nothing.

Four references, in practice: **which baseline · which instant · which population ·
which unit.** Two inputs disagreeing on any one of them produce a meaningless result
with an impeccable appearance.

The signature, so you recognise a new instance:

- the arithmetic is correct — no formula, sign or unit error
- each input is correct in its own source — checking one at a time finds nothing
- the result is plausible — right order of magnitude, right type, nothing absurd
- nothing accuses — no exception, no log, no empty cell, no red test
- **and the blame migrates**: it surfaces as poor performance, as delay, as low
  progress. The victim is usually the works or the crew, not the calculation.

That last one is why the defect survives. A number that accuses somebody is rarely
questioned by anyone except the accused.

**Where to look:** calculations with **two sources** — a plan value against an execution
value, an external reading against an internal accumulation, a numerator from one system
and a denominator from another. Most construction control indicators are exactly this
shape. **Where not to look:** single-source calculations. Summing columns of one table at
one instant cannot have this defect, and spending review effort there is what makes
review look expensive.

**Do not filter by size.** The same mechanism measured across fronts produced an error
worth a fraction of a percent of the budget in one and a third of an entire phase in
another. The size of the deviation depends on the file, not on the defect. **The check is
about whether the condition exists, not about whether the deviation hurts.**

Full case family: `references/datum.md`.

## Order of operations — the order is part of the method

### 1. Network integrity, before any discussion of dates

Nothing about dates is worth discussing until the logic holds. When the scheduling tool
recalculates over a violated network, **every trend date in the file is computed from
logic the works does not follow.** Arguing about a forecast date before this is arguing
about a figure derived from a false premise.

There is a misleading side effect: delay on stalled predecessors **stops propagating** to
the milestones, because the successors were already delivered. The schedule looks healthy
at the end precisely because it is broken in the middle.

### 2. Date adherence

### 3. Reporting consistency

The check catalogue, with stable codes and the exact criterion for each, is in
`references/checks.md`. The network rules as a decision table per relationship type, with the
lag, the both-complete exclusion and the measured effect of each criterion, are in
`references/network-rules.md` — written so another implementation can be aligned number for
number. Codes are **stable identifiers**: a finding keeps its code when
the implementation changes. Without that you cannot discuss a problem across weeks. Two
numberings exist in the wild for these same findings and **A1/A2 mean different things in
each** — `references/checks.md` says which set is canonical and maps between them. Never
quote a bare code across the two.

**One transversal rule, and it is the finest judgement in the whole set:** a predecessor
that is 100% physically complete with no actual finish is a **reporting** defect, not a
network breach. It migrates out of the network findings. Without that rule a
record-keeping problem is counted as an execution problem, and the conversation with the
people doing the work starts by accusing the wrong thing.

## Before writing the first comparison: units

Measured in MS Project, and it generalises to any scheduling tool: **duration, variance
and link lag are stored in minutes of work, not days** — and not 1440-minute days either,
but the working day configured in the file. Read the working day from the file rather than
assuming it; works run 8, 9, 10-hour days and shifts.

Converting lag by the working day yields **working days**. Using those as calendar days
errs by roughly 7/5 plus holidays, and **the error accumulates along the chain**.

The generalisable form: **every scheduling tool has an internal unit that is not the one
on screen.** Ask "what unit is this field stored in?" before writing the first
comparison, because the failure mode here is a plausible list, not an exception.

**And the conversion basis is per activity, not per file.** The working day belongs to the
calendar attached to that activity, in its own Calendar column, not to the project header.
Measured on one real programme: 107 calendars, most activities on a nine-hour six-day week
while the header declared eight hours over five days, and a rainy-season calendar holding 616
non-working days of weather reserve. Converting everything by the header flagged 27% of the
schedule as inconsistent with a median disagreement of two days, burying the 38 activities that
genuinely disagreed by more than sixty. Counting on each activity's own calendar brought it to
2% with the signal intact. **A construction schedule keeps its holidays, its shift pattern and
its productivity reserve in the calendars; leaving them out does not approximate the answer, it
invents one.**

Mechanics, with the measured cases: `references/reading-schedules.md`.

## Earned value must be computed, not read

Measured across several real files: **the calculated earned-value fields are not in the
file.** The tool does not persist calculated fields; it recalculates on open. A library
reading the file finds them null in 100% of rows, including in files where baseline cost
is populated — the reader is reading fine, the field is not there.

    earned value = baseline cost of the prevailing baseline x physical % complete,
                   accumulated to the status date

`measured`. That formula was reconciled **to the cent** against what the tool displays, on
both phases of a real schedule, in an independent verification recorded at the time — and the
skill now does that reconciliation itself on every run, because the XML export carries the
tool's own BCWP (the `.mpp` read through a library does not). On a 6,484-task programme:
4,676 of 4,677 leaves to the cent, the one difference an activity executed ahead of its baseline
window, which the tool credits nothing for until the status date reaches that window. Which
instant, again.

One caution that is not about arithmetic: **using physical percent complete is a business
rule, not a derivation.** Another organisation may weight by cost, by quantity or by a
regulator's schedule. State which one you used rather than presenting it as the definition.
And percent complete can be typed by a person rather than derived from work done, in which
case it is a declaration and earned value inherits that.

And **which baseline** feeds it is not a constant. A schedule that began as one phase and
grew can hold baselines in different slots, with the current one not in the default slot.
Getting this wrong is datum case #1: in the measured case the parser always used slot 0
while the live baseline sat in slot 1, so the earned value of a whole phase came out at
zero and overall progress read 8.95% where the correct figure was 19.93%. Less than half
the real value, and nothing looked wrong.

**Do not trust the file to tell you which slot.** The accessor for that setting returns
**0, not null** — constant, in every file, measured across six real schedules by two
independent parties. So the natural guard (`if (v != null) use(v)`) **passes**, the code
adopts slot 0 everywhere, and the wrong number arrives with *"the file declares slot 0"*
attached. False, and convincing. **A plausible default returned instead of null disarms the
check that would otherwise exist.** Null shouts; zero passes.

**Determine the slot from the data instead.** The prevailing baseline is **the
highest-numbered slot that has any leaf activity with cost greater than zero.** Summary
rows and external tasks do not vote — they carry rolled-up or foreign values and would
elect an empty slot. This is the defence adopted precisely because the declared setting
cannot be trusted, and it is an instance of a wider rule: **when the file already contains
the result of the expensive calculation, derive the setting from the data rather than from
a field that claims to declare it.**

S-curve and sampling rules, including why a costed milestone legitimately vanishes from a
phased S-curve while both figures stay correct: `references/earned-value.md`.

## Counting convention is part of the finding

"How many activities have the problem" depends on how you count. One set of violated
links yields three defensible answers depending on whether you count successors,
predecessors, or distinct activities involved in either role.

What decides is not the mathematics: **diverging from the counting convention of the tool
the other party uses is handing them the argument.** Align the count with what their tool
shows. Being right by another criterion is worth less than being checkable.

## Aggregates need their weight distribution

A healthy aggregate can be the average of two pathologies. A positive aggregate progress
figure can be out-of-sequence activities covering activities that should be complete and
sit at zero. **Every aggregate figure must travel with the distribution of its weight** —
otherwise the apparent advance shows up where the money is not.

## Comparing against the previous delivery

Everything above reviews one file. The other half of the method compares two snapshots of the
same schedule to answer what moved and whether it was execution or a replan, and to decompose
the aggregate deviation into per-activity contributions that sum to it. Matching activities
across versions, the three signals that separate execution from replan, and the reason a
changed baseline is a finding about the report rather than about performance, are all in
`references/comparing-versions.md`.

## The report

The deliverable is not the list of flagged activities. It is a report where **every
finding closes with where it came from**: which columns were used, which filter reproduces
it, which identifiers to check.

That turns the document from *"trust me"* into *"check it yourself"*, and it is the
difference between a report that carries a meeting and one that starts an argument.

Two consequences worth respecting:

- **Run where the data already is.** A check that needs an export, a conversion or a
  pipeline does not get run weekly. One that is a keystroke inside the scheduling tool
  does. This is not a limitation; it is what makes the check get used.
- **Flag and filter rather than producing a separate list.** The result should be
  navigable inside the schedule itself, with the activity in its context — that is what
  lets you check it together with the other party in the meeting.
- **Change nothing, and know how to undo.** Write only a marker field and the display,
  never schedule data, and ship a routine that clears the markers. A tool that dirties
  somebody else's file must know how to clean up. Run on a copy regardless.

## Carry provenance with every claim

This is not decoration, and dropping it is the one way to make this skill worse than its
source. Label every factual claim you make from this method:

| Label | Means |
|---|---|
| `measured` | somebody ran it, saw it, and the figure is here |
| `inferred` | plausible reasoning, **not reproduced** |
| `reported` | came from another party and **was not re-checked here** |

The reason is that half the value of accumulated knowledge is **not having to re-measure**,
and that promise only holds if it is clear what was actually measured. A third-party
report stamped as a measurement destroys the whole basis, because nobody knows what to
trust any more.

Two corollaries that earn their place:

- **Prove the probe can pass before trusting a negative result.** A search that finds
  nothing may mean the thing is absent or that the instrument is blind. Validate with a
  control you know is present.
- **A concrete, falsifiable recommendation beats a vague, irrefutable one.**

## Scope, honestly

- The mechanics here were measured on **MS Project** files, read both through in-tool
  macros and through a JVM parsing library.
- **Primavera P6 is not covered.** The method transfers; the field-level mechanics were
  not measured there. Do not assert P6 behaviour from this skill.
- Forensic delay analysis and the DCMA 14-point assessment are **adjacent and not
  included**. Say so rather than improvising them.

## Before anything from a review leaves the machine

Schedule review material carries third-party identity. Scrub before the first commit or
publish, not after — git history does not erase without a force push.

Never carries over: employer or contractor names, contract numbers, chainages or
stationing, person names, contract and works values, local paths that reveal an
employer's folder structure.

**The figure stays, the identity goes.** *"Validated on a road-concession programme, 6,483
tasks, reproducing the source tool to the cent"* has the same probative force as the named
version and none of the consequences. The evidence is the measurement and the date, not
the client.

One less obvious consequence: **an organisation's standard does not belong in the generic
method.** A specific field mapping is that organisation's asset. What is yours is the idea
that the mapping can be declared rather than coded.
