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
classification and the value come from different instants, and either reading alone is
defensible. A genuine datum instance.

**But the repair is not a sharper classifier.** `reported`: the cost was never lost because
of what the items *were*; it was lost because a zero-length span generates no time buckets.
Reconcile instead — the residue between baseline cost and the sum of the phased buckets goes
to the start day, on every task, checked by difference with no classification at all. See
`earned-value.md`.

The wider lesson is about repairs, not about milestones. **When a datum mismatch shows up, the
tempting fix is to make the two sides agree on the classification. The better fix is often to
remove the classification from the calculation.** A total that reconciles cannot disagree with
itself about which instant it was measured at.

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

## Appendix: what this family did to its own record

Worth keeping, because it is the method turned on itself.

Case #1 — earned value on the wrong baseline slot — has now been written **five times**, and
the middle versions were wrong with increasing confidence:

1. *"The library does not expose the setting."* False; the getter exists.
2. *"It exposes it, but the reader never populates it, so test for non-null."* Right in the
   first half. The second half was **inference presented as measurement**, from a static
   search.
3. *"It returns 0, not null."* Measured, across six schedules by two parties. Correct.
4. *"The 0 belonged to a different family of fields, and the formula was never reconciled
   against the tool."* Asserted from memory by the party that had originally measured it.
   It propagated: a downstream knowledge base downgraded a `measured` topic to `reported`
   on the strength of it.
5. **The dated record was read.** Version 3 was right, and the formula *had* been reconciled
   to the cent. Version 4 was a false memory, and the downgrade had to be undone.

Three things to take from it:

- **"I do not remember measuring that" is not "it was not measured."** Before contradicting
  a recorded claim, find the record. The party most likely to misremember a measurement is
  the one who made it, because they remember the reasoning and not the artefact.
- **A claim that survives being wrong twice is not thereby right the third time** — and,
  symmetrically, a correction from an authoritative source is not right either. Version 4
  came from the most credible possible source and was still false.
- **A retraction travels slower than the claim.** The downgrade reached the knowledge base
  within the hour; undoing it needed someone to go and read a dated file. Build the citation
  into the claim, so the next reader does not have to trust anybody's memory — which is the
  whole reason provenance labels exist.
