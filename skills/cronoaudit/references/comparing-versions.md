# Comparing two versions of the same schedule

`measured` — read from the comparison engine's source. The architectural decisions and the
field results are `reported`, from the documented creation record.

The single-version review (`checks.md`) asks *is this schedule internally consistent?* This
asks a different question: **what moved since the last delivery, and was it the works that
moved or the plan?**

The comparison is not the product. It is the means of producing the **cycle report**: planned
against actual progress, the deviation decomposed by discipline weighted by cost, milestones
with date movement, the next few weeks of trend, and the historical series for the contract.

## Input contract

Two snapshots of **the same schedule** — the previous delivery and the current one. Not two
different schedules, and not a schedule against an application's database: **each schedule
compared against itself**, which is what makes the reading defensible.

Each snapshot needs a status date and a saved baseline. Without the baseline there is no
planned half, and the deviation decomposition has no denominator.

Two entry modes exist, and the reason for the second is a real constraint worth knowing:
**a scheduling tool generally cannot open two independent instances the way a spreadsheet
can.** So either an outside process creates its own instance and opens both files, or the
comparison runs as an add-in inside the live tool, receiving the open file and opening only
the previous one.

## Matching an activity across versions — the hard part

A two-step cascade:

1. **The stable unique identifier.** Not the displayed row number, which renumbers freely.
2. **Failing that, name plus WBS path.** A cheap second chance that survives a renumbering.

Then two classes, and **only two**:

| Class | Meaning |
|---|---|
| INSERTED | present in the current version, no match in the previous |
| REMOVED | present in the previous version, never matched |

**Resist inventing more.** A renamed activity that also moved branch is indistinguishable from
a removal plus an insertion, and pretending otherwise manufactures a third category that
cannot be verified. Report the unmatched count as a number the reader must judge, not as a
classification you are confident about.

**Caveat on the identifier**, and it is measured: the unique identifier on the phantom row that
represents an inserted subproject is **local to the file**. Matching across files on it produces
false positives — and **a false positive here is worse than a failure to match**, because the
cascade resolves to the wrong pair instead of resolving to nothing. A pair that does not match
lands in the unmatched list where somebody looks at it. A pair matched wrongly produces a date
movement, a deviation and a trend entry for two activities that have nothing to do with each
other, all of them plausible. Exclude those rows rather than trusting the match.

**Summary rows and milestones are excluded** from deviation, trend and baseline comparison.
Summary rows would double-count their children; milestones have no duration and distort every
rate.

## The output: eight things, and what each answers

| Output | Answers |
|---|---|
| General, current | where does the contract stand now |
| General, previous | where did it stand last cycle, **by the identical rule** |
| Trend | which activities moved their dates in the live schedule |
| Baseline | which activities had their **baseline** dates changed |
| Decomposition | per-activity weighted contribution to the deviation |
| By discipline | the same contributions aggregated, ordered by magnitude |
| Unmatched | inserted and removed activities |
| Milestones | milestone date movement and count in delay |

**The second row is the whole discipline in one line.** Both snapshots' general indicators are
computed by **one reusable function called twice**, not by two code paths that happen to agree.
If the previous cycle's figure is computed a different way from the current one, the difference
between them is a datum artefact, and it will read as performance. Calling one function twice is
the cheapest possible guarantee that both halves share a reference.

The principle, worth stating in general because it applies far beyond schedules: **do not verify
that the two halves agree — construct them so that they cannot disagree.** A test that checks
two code paths against each other passes until the day somebody edits one of them. One code path
called twice has nothing to drift.

## Separating a change in execution from a change in plan

This is what makes the comparison mean something, and it comes out of three signals read
together:

| Signal | Reading |
|---|---|
| Dates moved **and** actual dates are populated | **execution** — the works happened differently |
| Dates moved, **no** actual dates | **replan** — somebody rewrote the forecast |
| **Baseline** dates moved | **the reference itself moved** |

The third is the one to look at first, and it is the datum family made visible instead of
inferred. **When the baseline changes between two cycles, your comparison basis moved
underneath the comparison.** Every deviation figure that straddles the change is measured
against two different references. Report it as a finding about the report, not as performance.

The second is where the conversation between the parties is won or lost. A forecast rewritten
with no execution behind it is a plan change, and it is legitimate — but it must be visible as
one, because otherwise next cycle's comparison starts from a baseline nobody agreed to.

## The deviation decomposition, and why it earns its place

Per leaf activity with baseline cost above zero:

    physical %   = BCWP / baseline cost x 100
    contribution = (BCWP - BCWS) / total baseline cost x 100

The second is **weight-relative**: it is that activity's share of the overall deviation in
percentage points, so the contributions **sum to the aggregate**. Activities whose
contribution rounds to zero are dropped, because a list of zeros hides the ones that matter.

This is the operational answer to the aggregate problem stated in `SKILL.md`. *"Every aggregate
figure must travel with the distribution of its weight"* is advice; **the decomposition is the
distribution**, and it is why a positive aggregate can be read on the spot as out-of-sequence
work covering activities that should be complete and sit at zero.

The denominator is the total baseline cost from the summary row, falling back to the sum of the
leaves when that is absent. **State which one was used**: a decomposition against a different
denominator is not comparable with last cycle's.

Aggregating the same contributions by discipline, ordered by magnitude rather than
alphabetically, puts the discipline that actually moved the number at the top. Ordering a table
of impacts by name is how the largest item gets missed.

## Persistence without infrastructure

There is no database. **Report N is the input to report N+1** — the historical series travels
inside the generated file itself. Consequences worth copying:

- the series is auditable by anyone holding the file, with no access to grant;
- there is nothing to deploy, migrate or back up;
- and the cost: the chain breaks if a cycle's file is lost, so the file is the asset.

The generated report is also **self-contained**: the template lends its own code to the output,
so a recipient needs nothing installed to use the report's buttons.

## Trend from the live schedule, not from the baseline

Stated as an architectural decision, and the reasoning is the strongest single argument in the
comparator: **the baseline's planned dates, by definition, never vary between two runs.** A
trend computed from them is a constant dressed as a forecast. The trend that informs a decision
is the one the live file currently projects.

## The anchor by field convention — and what generalises

The milestone structure is detected by which corporate field is populated. That mapping is the
organisation's asset and does not transfer.

**What transfers is that the mapping should be declared, not coded.** A field binding written as
a constant makes the tool single-organisation; the same binding read from a declared profile
makes one codebase serve many. This is the difference between a script and a product.

## The comparator's own datum bug, which is the best case in the set

A revision corrected a defect where the actual progress figure came out **14.62% when the true
figure was 23.57%**.

The cause: the engine used the tool's **native** earned-value field, which always answers about
baseline slot 0. **The planned half was already reading the correct slot.** So one indicator had
its two halves measured against two different baselines — and the gap between them surfaced as
**performance deviation**, attributing to the works a shortfall that belonged to the reference.

This is datum case #2 (`datum.md`), found in production, in a tool built by someone who knew
about the slot problem. **Knowing a failure class does not immunise you against it.** The defence
is the check, not the knowledge: compute both halves of every indicator from one explicitly
chosen reference, and say in the output which one it was.

## What it produced, with labels

- The reports were **adopted for internal, managerial and shareholder reporting** (`reported`).
- The reporting cycle went from **hours to under 10 minutes** (`reported`, practice observation,
  not timed).
- **Six consecutive weekly windows** consumed through the interface without interruption
  (`measured`).
