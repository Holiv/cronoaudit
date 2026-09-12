# Reading a schedule programmatically — the measured traps

All `measured` on MS Project files, read through in-tool macros and through a JVM parsing
library. **Not measured on Primavera P6.**

## Time is stored in minutes of work

`measured`. Duration, variance and link lag are stored in **minutes**, and the day is the
**working day configured in the file**, not 1440 minutes.

A 30-day threshold written as `30` matches almost nothing. Written against an 8-hour day it
is `30 x 480 = 14400`. A tolerance written as `1` meaning "one day" becomes one minute, and
the check then accuses nearly every activity.

Rules:

1. **Read the working day from the file.** Do not assume 480 — works run 9 and 10-hour days
   and shifts.
2. Define it once and derive every threshold from it.
3. Never write a day count directly into a comparison.

The failure mode is the expensive one: no error, no exception, no warning — **a wrong list
that looks right**, because it returns a list.

### Lag is the same rule, and the error is bigger

`reported`. Link lag is also in minutes of work. Converting by the working day yields
**working days**; using those as calendar days errs by roughly 7/5 plus holidays, and **the
error accumulates along the chain.**

A start-to-start lag of −51840 minutes is −108 working days, which is −151 calendar days:
43 days of error in a single link.

Measured on a schedule of 164 activities and 188 links: propagating delay with **no user
adjustment at all**, 32 of the 164 nodes already left their planned position, the worst
displacing 341 days. The screen would open with 32 red bars reading "pushed by the chain"
without anyone having touched anything — and **every date plausible.**

**The fix is not a better conversion factor.** Converting by the working day and applying
7/5 still mishandles holidays. Derive the constraint from what the plan already practises:
take **the smaller of the converted lag and the distance the plan already realises between
those two activities.** The plan has already absorbed the real calendar, so it is a better
authority on the interval than any factor you can compute.

Two companions, both `reported`:

- **Propagate the delta, not the absolute date.** Pushing an absolute date discards whatever
  the plan encoded about that activity; pushing a displacement preserves it.
- **An effective start lands on the successor's next working moment**, not on the instant the
  arithmetic produces. Otherwise work is scheduled into a gap the calendar does not have.

## The eleven baseline slots

`measured`. The tool keeps **11 baselines**: the unnumbered one plus 1 through 10. A
schedule that starts partial and grows can hold baselines in different slots — in the
measured case the first phase stayed in slot 0, from when the file only had that phase, and
the whole file went to slot 1, saved later.

Which slot feeds the earned-value calculation is **a setting of the file**, defaulting to
slot 0.

### Determine the prevailing slot from the data, not from a field

`reported`, and this **corrects an earlier version of this document.** Which slot feeds the
earned-value calculation is a setting of the file, defaulting to slot 0 — but do not try to
read it. Determine it:

**The prevailing baseline is the highest-numbered slot with any leaf activity whose cost is
greater than zero.** Summary rows and external tasks do not vote. They carry rolled-up or
foreign values, and letting them vote elects a slot that holds nothing.

An earlier version of this document claimed the accessor for that setting returns `0`
instead of `null`, and built the lesson on that. **The attribution was wrong.** The
`0`-instead-of-`null` trap is real and was measured, but it belongs to **custom numeric
fields that were never configured** — a schedule where nobody populated them returns 0 from
every one, indistinguishable from a real zero.

The lesson survives the correction, and applies wherever you meet it:

**An accessor returning a plausible default instead of null disarms the check that would
otherwise exist naturally.** The natural defence writes itself:

```
if (v != null) use(v);
```

**With null that guard protects. With zero it passes** — and the wrong value arrives
carrying the sentence *"the file says so"*. False, and convincing. Borrowed authority is
worse than an unexplained error. It holds for any API where 0, empty string, `false` or
"today" are legitimate domain values: you cannot distinguish "unknown" from "this is it"
when both have the same representation.

**The test, with the right criterion:** not *"did it return non-null?"* but **"did it return
something other than the default on at least one case known to differ?"** While the answer
is always the default, the field carries no information.

And the correction itself is the more useful lesson. Two earlier versions of this claim were
wrong, each confidently. The sequence: first *"the library does not expose the setting"*
(false, the getter exists); then *"it exposes it but the reader never populates it"*
(inferred from a static search, not measured); then a measured zero attributed to the wrong
family of fields. **A claim that survives being wrong twice is not thereby right the third
time.** Carry the label.

## The calculated fields are not in the file

`measured`. BCWP and BCWS **do not come from the file.** Measured across three schedules by
two independent parties: null in 100% of rows in all of them. The control that closes the
argument: in the largest file, most rows had baseline cost populated. The reader is reading
the file; the calculated field is not there.

The tool does not persist calculated fields; it recalculates on open. Anyone reading through
a library must compute:

    earned value = baseline cost x physical % complete

`reported`, and **narrower than an earlier version of this document claimed.** What was
reconciled to the cent was **baseline cost and a legacy extraction — not earned value**,
which the tool does not expose in a comparable form. So the mechanism is right and the
output is unproven. Say that, rather than lending the figure the authority of a match that
was about something else.

Note also that **physical percent complete is a business rule**, not a definition. Another
organisation weights by cost, by quantity, or by a regulator's schedule. And percent
complete can be typed by a person rather than derived, in which case it is a declaration
and earned value inherits that.

## Material resources

`reported`. Material resource assignments were not being read at all. Two causes:

- the convenience accessor for resource names comes back empty — **iterate the assignments
  and filter by resource type** instead;
- material **units arrive in hundredths**, and work is equivalent to quantity.

Same category as the minutes trap: an internal unit that is not the one on screen. One file
in the measured set carried 4,554 material assignments.

## The WBS number lies about the branch

`reported`. The WBS numbering can misrepresent which branch an activity belongs to — a
side effect of an inserted subproject. **The parent chain is correct even when the WBS
number is wrong.** Never identify a branch by its number; walk the parents.

## The subproject phantom-row identifier is local

`measured`. The identifier on the phantom row representing a subproject is local to the
file. **Matching on it produces false positives** across files.

Related and more general: the displayed row ID and the stable unique ID are different
fields. The stable one is what code should join on; the displayed one is the only one a
person can see on their screen. **Keep the mapping between them** — it is what lets you ask
a human to verify a specific finding.

## Cost may be apportioned rather than priced

`reported`. In one measured file, 119 leaf activities carried only 37 distinct cost values —
the cost was apportioned across activities, not priced per activity. Consequence: **the cost
weight used for progress does not represent value.** Report weighted progress with that
caveat, or the weighting implies a precision the source does not have.

## Two implementation traps for any localised tool

- **Field names are translated.** Resolve them at run time rather than writing a localised
  literal, or the code breaks on a differently-localised install.
- **A generated spreadsheet carries no formula results.** A file written by a script has the
  formula but not its cached value, and the cell carries the value tag **present and empty**
  — which makes the naive check pass. Verify the key, not the count.
