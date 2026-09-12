# Earned value, S-curves and sampling

## Compute earned value; do not read it

See `reading-schedules.md` for the measurement. Summary: the calculated fields are absent
from the file, so

    earned value = baseline cost x physical % complete

and **which baseline** is a per-file setting the library reports unreliably. Getting the
slot wrong is datum case #1 and moves the figure by more than half its value while looking
entirely normal.

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

**The criterion, measured:** a milestone is **declared a milestone AND has baseline
duration zero**. Neither condition alone works — see datum case #3, where classifying by
current duration and summing baseline cost mixes two instants.

**The size, when it appears:** summed across seven work fronts, a large amount of budget
sits outside the curve; in one front, milestones were 35% of the entire pre-works phase.

And the milestone names explain why this concentrates in pre-works: outorgas, licences,
judicial processes, cadastral surveys, permit issuance. **Fees and licences are real money
with no duration.** Watch also for milestone names ending in "(not applicable)" — that
denounces a copied template where someone kept the row and the cost came along with it.

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
