# Network quality — does the schedule hold up as a model?

`measured` on a 6,484-task export. An implementation of the mechanical metrics of the
DCMA 14-point schedule assessment, with the published thresholds quoted, plus the
qualitative parameters a planner asks of any schedule. **Implementation, not certification.**
The thresholds are written down so they can be argued with; the counting conventions are
declared; and what a file cannot answer is said, not approximated.

Population: leaf, active, non-external activities; milestones included unless stated;
working days on each activity's own calendar.

| Code | Metric | Population | Threshold | Reads |
|---|---|---|---|---|
| Q1 | Missing logic | incomplete, non-milestone | ≤ 5% | no predecessor or no successor: delay that does not propagate |
| Q2 | Leads | links | 0% | negative lag hides an overlap the logic should model |
| Q3 | Lags | links | ≤ 5% | positive lag is time nobody owns |
| Q4 | Relationship types | links | ≤ 10% non-FS | each non-FS link deserves a reason |
| Q5 | Hard constraints | incomplete | ≤ 5% | MSO, MFO, SNLT, FNLT pin a date against the logic; SNET and FNET are counted, not failed |
| Q6 | High float | incomplete | ≤ 5% | more than 44 working days: usually an unconstrained milestone |
| Q7 | Negative float | incomplete | 0% | a date the logic cannot meet |
| Q8 | High duration | incomplete, non-milestone | ≤ 5% | more than 44 working days remaining: too coarse to control |
| Q9 | Invalid dates | all leaves | 0% | actual dates after the status date; forecast dates in the past are the H finding |
| Q10 | No resource | incomplete, non-milestone with duration | count | nothing to trend |
| Q11 | Missed activities | due by the status date on the baseline | ≤ 5% | not finished on time |
| Q12 | Critical path test | — | — | needs the schedule perturbed; **not computable from a file** |
| Q13 | Critical path length index | — | — | meaningful only with a deadline on the finish milestone; **reported as not meaningful otherwise** |
| Q14 | Baseline execution index | due by the status date | ≥ 0.95 | finished on time ÷ due |

Beyond the fourteen: summary tasks carrying links (logic belongs on activities), milestones
without a deadline, whether the critical chain reaches the final milestone, and the count of
critical incomplete activities.

## Reading it

Run before the date discussion, in this order: **Q1, Q2, Q5, Q7 first.** A schedule failing
those is not a model of the works, and every forecast date it produces is a number with no
basis. Q6 and Q8 say whether it can be *controlled*. Q11 and Q14 say whether it has been
*kept*.

On the real programme, before any action: 29 open ends among 5,251 leaves, 14 leads, 58 lags,
193 non-FS links, 46 soft constraints and no hard ones, 3,450 activities above 90 working days
of float against zero milestones with a deadline — which is the same finding read from two
sides.
