# Earned value, S-curves and sampling

## Compute earned value; do not read it

See `reading-schedules.md` for the measurement. Summary: the calculated fields are absent
from the file, so

    earned value = baseline cost of the prevailing baseline x physical % complete,
                   accumulated to the status date

**Which baseline is prevailing is not declared by the file.** Derive it: the highest-numbered
slot with any leaf activity carrying cost above zero, with summary rows and external tasks
excluded from the vote. Getting this wrong is datum case #1 and moves the figure by more than
half its value while looking entirely normal.

**The output of this formula has not been reconciled against the tool's own earned value**,
because the tool does not expose it comparably. Baseline cost and a legacy extraction were
reconciled to the cent; earned value was not. Right mechanism, unproven output — state it
that way.

**Also beware the manually-entered percent complete.** Percent complete can be typed by a
person rather than derived from the work done. When it is, it is a declaration, not a
measurement — and earned value computed from it inherits that. State which it is.

## A costed milestone legitimately vanishes from a phased S-curve

`reported`, with two of the three figures independently measured.

**The question:** the schedule's baseline cost does not match the budget of the S-curve
generated from the same file. Which one is wrong?

**Neither.** A phased S-curve distributes each activity's cost **across the time it
occupies**. A milestone has zero duration: it occupies no time, generates no phasing, and
its cost **does not enter the curve** — while sitting correctly in the baseline.

Each figure is right in its own source. It is the comparison that is meaningless without
the adjustment, and that is why the divergence survives review: whoever checks the schedule
finds it correct, and whoever checks the curve does too.

**Do not fix this by classifying milestones.** `reported`, and it **corrects an earlier
version of this document**, which claimed the criterion was a conjunction of the milestone
flag and zero baseline duration. There is no flag test, and there should not be one.

What actually loses the cost is the phasing condition **finish greater than start**. An item
whose finish equals its start produces no time buckets, so its cost has nowhere to land. That
is not a property of milestones; it is a property of zero-length items, and the milestone flag
is neither necessary nor sufficient to identify them.

**The fix is a reconciliation, applied to every task, not a classification applied to some:**

    residue = baseline cost - sum of the phased buckets
    if residue != 0: place the residue on the start day

Checked **by difference**, with no flag anywhere. This is strictly better than a classifier
for three reasons, and the reasons generalise:

- it needs no criterion to be right, so it cannot be wrong about an edge case;
- it catches every other way cost can fall out of the phasing, including ways nobody has
  found yet;
- it is self-verifying — a nonzero residue after the fix is a defect report, not a silent
  loss.

**Prefer reconciling a total to classifying its members.** A classifier fails silently on the
case it did not anticipate; a residue check fails loudly on all of them.

**The size, when it appears:** summed across seven work fronts, a large amount of budget
sits outside the curve; in one front, milestones were 35% of the entire pre-works phase.

And the milestone names explain why this concentrates in pre-works: outorgas, licences,
judicial processes, cadastral surveys, permit issuance. **Fees and licences are real money
with no duration.** Watch also for milestone names ending in "(not applicable)" — that
denounces a copied template where someone kept the row and the cost came along with it.

## Dating consumption over time

`reported`. When distributing a resource's consumption across a period, the dates that govern
are **the assignment's own dates, not the activity's** — and where a task was suspended and
resumed, consumption runs **from the resume**, not from the original start. Treating the
suspension as if it never happened attributes work to a window in which none occurred, and
the monthly figure then disagrees with the source tool by the whole of one activity.

Same family as the unit traps: the interval you assume is not the interval the file records.

## Reconciling weekly measurement with a monthly reporting point

`measured`. Measurement happens weekly on a fixed weekday; the report wants one point per
month on a fixed day. The two dates almost never coincide. Which week represents the month?

**The tolerance comes from the calendar, not from taste.** With weekly measurement on
Sundays and a monthly point on the 10th, the distance from the 10th to the nearest Sunday
never exceeds 3 days. Computed over the 48 months of a four-year window:

| distance | months |
|---|---|
| 0 days | 6 |
| 1 day | 14 |
| 2 days | 14 |
| 3 days | 14 |
| maximum | 3 |

The 42 months that do not land exactly split into three equal parts. That is not an artefact
of the window chosen; it follows from 7 not dividing month lengths.

So a tolerance of 3 is derived: **within 3 days the week exists**, and the tolerance never
manufactures a false gap when the archive is complete; **beyond 3 days the week is genuinely
missing**, and the tolerance exposes an incomplete archive rather than disguising it. Any
smaller value invents gaps; any larger one hides real absences.

### Always sampling the previous measurement biases low

The lazy choice is "take the last measurement up to the date". That compares an exact planned
value on a date against an actual from up to six days earlier, and **produces negative
deviation by construction**, every month, with nothing actually late.

**The nearest measurement is the right one, even when it falls after the reporting point.**

### The nuance that nearly got the fix rejected

More valuable than the rule itself. The system held a legitimate guard: **reject future
dates**. It was nearly used as grounds to refuse "use the later week".

They are different things:

- the guard is about **import** — a file with a status date running ahead distorts the whole
  curve, and refusing is correct;
- the choice of week is about **display** — the data already exists and was already measured,
  and the question is only which of them best represents the month.

Applying the import rule to the display layer looks like rigour and is an error. **Before
invoking an already-accepted principle, check which layer it was made for.** A true principle
cited in the wrong place is harder to overturn than a weak argument, because everyone already
agreed with it once.

### A cumulative series makes the gap harmless

If a month has no measurement, that period's work is not lost — it sits inside the following
month's value, because the series is cumulative. That is what licenses **showing the hole**
instead of interpolating. An interpolated point is indistinguishable from a measured one once
the chart is rendered, and nobody goes back to check.

## Series identity: front and phase are independent axes

`measured`. "Whose is it" (contractor, contract, company) and "what stage is it in"
(pre-works, works) are different questions. Collapsing them forces you to invent fronts the
contract does not have. **The pair identifies the series; neither alone is sufficient.** When
the missing axis was added, eight sections that had been colliding on the same key stopped
colliding.

## A categorical axis keyed by its label

`reported`. On a categorical axis the **label is the key**. A `dd/MM` label repeats across
years, so interaction binds to the first matching point — four years of wrong readings, each
with a plausible value.

## A temporal archive with detail only on the latest snapshot

`reported`. "Most recent" is not the same as "the one with data". A retroactive import wrote
zero tasks, and a query selecting by maximum date returned empty **silently**. Select by
having-data, not by being-latest.
