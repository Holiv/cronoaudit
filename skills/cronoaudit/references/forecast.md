# Looking forward from the schedule

Five readings, all from data the file already carries. Each says what it is built on.

## Earned Schedule

Classic earned-value schedule measures are in money: SV = EV − PV, SPI = EV ÷ PV. They have a
known defect. As the project ends, EV reaches the budget whatever happened, so SV goes to zero
and SPI to 1.0 on a project a year late. The indicator improves with age and says nothing in
the last third.

**Earned Schedule** (Lipke, 2003) asks instead: *on what date did the planned curve reach the
value earned today?* Take today's EV, go up to the planned curve, read the date. That date is
ES, and it is schedule measured in time.

| Quantity | Formula | Reads |
|---|---|---|
| ES | date at which cumulative PV equalled today's EV, interpolated inside the month | where the plan said we would be |
| AT | actual time: days from the first planned day to the status date | |
| SV(t) | ES − AT | days behind the plan, negative is behind |
| SPI(t) | ES ÷ AT | schedule efficiency; 0.90 is ten percent slower than the plan |
| PD | planned duration: first planned day to the last baseline finish | |
| IEAC(t) | PD ÷ SPI(t), as a date from the first planned day | independent finish at this efficiency |
| TSPI | (PD − ES) ÷ (PD − AT) | efficiency the remainder needs to finish on the planned date |

**TSPI is the meeting number.** Above 1.0 the remainder must run faster than the plan; above
1.10 the literature treats it as unrecoverable, because no works sustains ten percent above plan
for long. It turns "we are late" into "we need this much more per week, and that is or is not
possible".

**The limits, stated in the report.** It is an aggregate, cost-weighted measure. It does not see
the critical path: a mass of non-critical activities late shows behind while the end date
holds, and the reverse. So it never replaces the schedule's own finish; it is set beside it,
and the gap between the two is the conversation. It inherits everything the planned curve
inherits: the baseline slot, the earned-value method, costed milestones, execution ahead of the
baseline window.

## Look-ahead

Four and eight weeks from the status date: what must start and what must finish, by group,
weighted by baseline cost; the earning the file plans for the window, pro-rata from the phased
curve; and the earning the last two months' practised rate would deliver. One word says whether
the planned measurement of the window is reachable.

## Rates by group

Earned percent per week to date, from the group's first earning, against the percent per week
the remainder needs to land on the group's last baseline finish. The ratio required ÷ practised
gives one word per group: on pace, stretch, out of reach.

## Milestone bands

The distribution of finish slippage — current finish minus baseline finish, calendar days —
across started or due activities in this snapshot, applied to each future milestone's current
finish as P50 and P80. **Empirical, not a simulation with an invented premise.** A series of
snapshots replaces it with observed cycle-to-cycle movement.

## Rainy-season exposure

Remaining cost spread evenly over each activity's current span from the status date, read
against the months its own calendar reserves for bad weather — a month with four or more
non-working exceptions. Reported now, and again with everything slipped thirty days, because
slipping into the reserve is how a small delay becomes a large one. `inferred` on the spread,
`measured` on the reserve months.
