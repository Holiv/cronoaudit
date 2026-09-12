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

**The fix is not a better conversion factor.** 7/5 still mishandles holidays. Derive the
constraint from what the plan already practises rather than recomputing it.

## The eleven baseline slots

`measured`. The tool keeps **11 baselines**: the unnumbered one plus 1 through 10. A
schedule that starts partial and grows can hold baselines in different slots — in the
measured case the first phase stayed in slot 0, from when the file only had that phase, and
the whole file went to slot 1, saved later.

Which slot feeds the earned-value calculation is **a setting of the file**, defaulting to
slot 0.

### The accessor returns 0, not null — and that is worse

`measured`, after two wrong intermediate conclusions. The sequence matters more than the
result:

1. *"The library does not expose the setting."* **False** — the getter and setter exist.
2. *"It exposes it but the reader never populates it, so test for non-null."* Right in the
   first half, **dangerous in the second**. That was inferred from a static search, not
   measured.
3. **Measured:** the accessor returns **`0`, constant, in every file.** Verified on six real
   schedules by two independent parties, of sizes from tens to over a thousand tasks, with
   control fields populated on the same object to rule out a failed read.

Why zero is worse than null. The natural defence writes itself:

```
if (v != null) useSlot(v);
```

**With null that guard protects. With zero it passes** — the code adopts slot 0 on every
file, convinced the file said so. And the wrong number arrives carrying the sentence *"the
file declares slot 0"*: false, and convincing. Borrowed authority is worse than an
unexplained error.

**The lesson that generalises:** an accessor returning a **plausible default** instead of
null **disarms the check that would otherwise exist naturally.** Null shouts; zero passes.
It holds for any API where 0, empty string, `false` or "today" are legitimate domain
values — you cannot distinguish "unknown" from "this is it" when both have the same
representation.

**The one-line test, with the right criterion:** not *"did it return non-null?"* but
**"did it return something other than 0 on at least one file known to use a different
slot?"** While the answer is always 0, the field carries no information — and a future
library version could start populating it without any signature changing.

## The calculated fields are not in the file

`measured`. BCWP and BCWS **do not come from the file.** Measured across three schedules by
two independent parties: null in 100% of rows in all of them. The control that closes the
argument: in the largest file, most rows had baseline cost populated. The reader is reading
the file; the calculated field is not there.

The tool does not persist calculated fields; it recalculates on open. Anyone reading through
a library must compute:

    earned value = baseline cost x physical % complete

In the measured case that formula matched what the tool shows **to the cent**, in both
phases. That is the kind of reconciliation worth doing once and never arguing about again.

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
