# The datum family — four measured cases, one signature

`inferred` as a family: the four cases below are each `measured` and documented
individually. The family is a generalisation from four cases in one ecosystem over two
weeks. It is not a law; it is a pattern that repeated often enough to be worth looking
for.

## Why "datum" is the right name

In surveying, the **datum** is the reference surface every elevation is measured against.
Two elevations can be perfectly measured and the difference between them entirely false,
if each was surveyed against a different datum. Nobody miscalculates. The subtraction is
correct. The result means nothing.

**The arithmetic is correct in all four cases below.** The defect is one layer earlier:
the inputs do not share a reference.

## 1. Earned value resting on the wrong baseline slot

The indicator was computed against baseline slot 0, which in that file was a leftover; the
current baseline was in slot 1. Progress came out at 14.62% where the real figure was
23.57%.

## 2. One indicator with its two halves on different baselines

Same file: the *planned* half rested on the current baseline and the *actual* half on the
old one. Each half correct in its own source, and the difference between them surfacing as
**performance deviation** — attributing to the works a delay that belonged to the
reference.

This is the purest form of the family. Nothing in the output distinguishes it from real
underperformance.

## 3. Classify by the present, measure by the plan

Calling something a milestone by its **current** duration, then summing its **baseline**
cost. In the measured set, 268 activities had exactly one of the two zeroed — the
classification and the value come from different instants.

The fix is to make the criterion a conjunction on the same instant: declared a milestone
**and** baseline duration zero. Neither condition alone is sufficient. When the criterion
was tightened this way, a standing anomaly — one schedule with cost on a zero-duration item
that did not diverge — **dissolved** rather than being explained. An anomaly that vanishes
when you sharpen the rule is a sign the rule was loose, which is different from an anomaly
that gets explained.

## 4. Deriving as if time did not pass

A dated official reading combined with hours confirmed after it, matched by presence rather
than by recency: the old value wins forever. The datum here is temporal, but the mechanism
is identical. A fact with a date is true **on** that date, not forever.

## The question that finds the fifth

> **Are all the inputs to this calculation measured against the same reference?**

The four references: **which baseline · which instant · which population · which unit.**

## How these were actually found

None of the four surfaced from a process or a checklist. All four surfaced because somebody
went to check one thing and looked at the row underneath.

The technique that closed the hardest of them, after seven hypotheses had been discarded by
measurement and none was the cause: **take one activity, one interval, and put the numbers
side by side.** Not aggregate analysis. One row, one window, both figures visible.

The companion discipline: **reproduce the figure the source tool shows**, not merely
demonstrate that yours differs. In one reconciliation of material distributed over time the
system computed one figure where the tool showed a substantially larger one, with a single
activity accounting for the entire monthly deviation. The cause was a task
suspend-and-resume mechanism: consumption restarts at the resume, not at the original
start. After the correction, in the same window and the same file, the previously wrong
material matched the source tool and the previously correct one **kept** matching.

That second half is the test that matters. **A correction that fixes one case without
breaking the other** is the evidence; a tool only tested where the answer was already known
has not been tested.
