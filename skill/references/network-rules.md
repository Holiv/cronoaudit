# Network integrity rules, exactly as implemented

`measured` on a 6,484-task export. This is the decision table the checks run; it exists so
that any other implementation — an in-tool macro, a spreadsheet — can be aligned number for
number. Every convention here was written down when it was decided, not when it first cost
someone half a day.

## Universe

- **Leaf** activities only: not summary. **Active** only. **Not external.**
- **Milestones are in** every check except G.
- **Pending record migrates first.** A predecessor with physical percent ≥ 100 and no actual
  finish is a record defect (P). Its links are **not evaluated** for A1 or A2, and the
  successor is not marked on that link. Without this rule a reporting problem is reported as
  an execution problem.

## Quantities

| Symbol | Meaning |
|---|---|
| `AS`, `AF` | actual start, actual finish |
| `L` | link lag in minutes of working time, negative for a lead |
| `wm(a → b)` | signed working minutes from `a` to `b` on the **successor's calendar**, negative when `b` is earlier |
| `day` | the successor's calendar working day, in minutes |

The calendar choice is a convention and is declared in the output. The lag is honoured on
every type: an intentional overlap under a lead is not a breach.

## Decision table

Evaluated per link, from the successor's side. `s` is the successor, `p` the predecessor.

### Finish-to-start (FS · TI)

| Successor | Predecessor | Result |
|---|---|---|
| has `AF` | no `AS` and no `AF` | **A2** total inversion |
| no `AS` | any | nothing |
| has `AS` and `AF` | has `AF` | **out of the count, by decision.** If `p.AF > s.AS` the pair is recorded under `ignored.A1_both_complete` with the overlap in days, for the forensics. |
| has `AS`, no `AF` | no `AF` | **A1** `pred_not_finished` |
| has `AS`, no `AF` | has `AF` | `gap = wm(p.AF → s.AS)`. **A1** `pred_finished_after_start` if `gap < L`. Reported `overlap_beyond_lead_days = (L − gap) / day`. |

With `L = 0` the last row reads: breach if the predecessor finished after the successor
started. With `L = −2 days` it reads: breach only if the overlap exceeded two working days.

### Start-to-start (SS · II)

| Successor | Predecessor | Result |
|---|---|---|
| has `AS`, no `AF` | has `AS` | `gap = wm(p.AS → s.AS)`. **A1** `ss_before_lag` if `gap < L`. |
| has `AS`, no `AF` | no `AS` | **A1** `ss_pred_not_started` |
| otherwise | | nothing |

### Finish-to-finish (FF · TT)

| Successor | Predecessor | Result |
|---|---|---|
| has `AF` | has `AF` | `gap = wm(p.AF → s.AF)`. **A1** `ff_before_lag` if `gap < L`. |
| has `AF` | no `AF` | **A1** `ff_pred_not_finished` |
| otherwise | | nothing |

The both-complete exclusion does **not** apply here: both finished is the only state in which
a finish-to-finish link can be judged at all.

### Start-to-finish (SF · IT)

| Successor | Predecessor | Result |
|---|---|---|
| has `AF` | has `AS` | `gap = wm(p.AS → s.AF)`. **A1** `sf_before_lag` if `gap < L`. |
| has `AF` | no `AS` | **A1** `sf_pred_not_started` |
| otherwise | | nothing |

## Marking and counting

- **Both ends of a violated link are marked**: the successor and the predecessor each get a
  row, with `role`, the counterpart's row number and the relationship type.
- The output carries **three counts**: distinct activities, as successors, as predecessors.
  Align with whatever convention the other party's tool shows.
- The output declares **which relationship types were evaluated and how many of each**, so
  silence about start-to-start links cannot be mistaken for coverage.
- Pairs are exported as `pairs.A1` and `pairs.A2`, each with successor and predecessor row
  numbers, the type, and the reason code.

## Measured effect of the criterion

Same 6,484-task export, before and after the rules above:

| | Pairs |
|---|---|
| FS, predecessor not finished | 47 |
| FS, predecessor finished after the successor started, beyond the lead | 17 |
| SS, started before the lag allowed | 7 |
| SS, predecessor never started | 5 |
| **In the A1 count** | **76** |
| FS, both complete with inverted order — recorded, out of the count | 179 |
| Overlaps that a lead covered — not accused | 14 |

The 179 is the number a meeting will ask about when two implementations disagree, and the
answer is the row above it: by decision, a pair that is finished no longer changes a
forecast, but it stays in the data because it is evidence of how the works was executed.

## Reason codes

Stable in the data; worded per language in the report.

| Code | Meaning |
|---|---|
| `pred_not_finished` | FS: predecessor has no actual finish |
| `pred_finished_after_start` | FS: predecessor finished after the successor started, beyond the lead |
| `ss_before_lag` | SS: started before the lag allowed |
| `ss_pred_not_started` | SS: predecessor never started |
| `ff_before_lag` | FF: finished before the lag allowed |
| `ff_pred_not_finished` | FF: predecessor not finished |
| `sf_before_lag` | SF: finished before the lag allowed |
| `sf_pred_not_started` | SF: predecessor never started |
