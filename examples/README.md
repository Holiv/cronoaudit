# Example: a fictitious road project, two deliveries

Português: [LEIA-ME.md](LEIA-ME.md)

Two snapshots of the same schedule, one month apart, to try cronoaudit on something
that reads like a real road job:

| File | Status date | Role |
|---|---|---|
| `rodovia-ficticia-rev03.xml` | 30/09/2026 | previous delivery |
| `rodovia-ficticia-rev04.xml` | 30/10/2026 | current delivery |

**Everything in them is invented.** The road (RF-140), the stretch (km 12+000 to
km 36+000), the client, the contractor, the quantities, the unit prices and every date
were made up for this example. No real project, company, contract or place is
represented.

## What is in the schedule

- 142 activities under 32 summary rows, about 220 links, 38 resources, task names in
  Brazilian Portuguese.
- WBS by stretch and discipline: contractual milestones, mobilisation, four 6 km
  segments (earthworks, drainage, paving, signing, lighting), a viaduct, demobilisation.
- Two calendars, both with the Brazilian national holidays and a rainy-season reserve
  from December to March: the project calendar (five days) and the earthworks calendar
  (six days). Each resource also carries its own calendar derived from one of the two,
  which is how MS Project saves a resource and what it expects when it opens the file.
- Nine milestones, each with a deadline.
- A cost-loaded baseline (unit prices times quantities), **distributed in time** one
  block per working day, so planned-to-date, SV, SPI and Earned Schedule are computable.
  Money is stored in hundredths, as the XML format does: a budget of 17,499,283,800 in
  a sidecar is R$ 174,992,838.00.
- Two custom fields, `DISCIPLINA` and `SEGMENTO`, for `--group-by`.

Most of it is healthy on purpose. The dates, float and critical flags come from a
forward and backward pass over the links and calendars, so they agree with the logic.

## Run it

```
python3 skills/cronoaudit/scripts/review.py \
    examples/rodovia-ficticia-rev03.xml examples/rodovia-ficticia-rev04.xml \
    --outdir out --lang pt
```

Add `--group-by DISCIPLINA` to weigh progress by discipline instead of by segment.
One file alone gives the review of that delivery; rev03 on its own is clean.

To see it in MS Project: File > Open, choose the XML, "As a new project"
("Abrir como novo projeto").

## What was planted, and where the report shows it

Row numbers are those of rev04.

| # | Planted | Where it shows |
|---|---|---|
| 1 | Real progress in October on a dozen activities | Cycle: dates moved with actuals behind them (execution); earned 23.44% to 28.01% |
| 2 | Row 63, *Sarjetas e valetas — Seg. 2*: start held to 28/12/2026 by a start-no-earlier-than constraint, 46 days later than in rev03, nothing executed | Cycle: replan; logic, one constraint added |
| 3 | Row 36, *Imprimação — Seg. 1*, started on 29/10 while row 35, *Base de brita graduada — Seg. 1*, is still open | Finding A1, out of sequence, both ends marked |
| 4 | Rows 77, 89, 136 and 170 have no successor | Network quality Q1 (4 of 96, under the threshold, so the network reads as linked) |
| 5 | The same four, plus the inserted row 57, carry 79 to 205 days of float | Network quality Q6 |
| 6 | Row 55, *Aterro compactado — Seg. 2*: 95% complete by duration, 57% physical | S-curve: the other earned-value method would read 0.44 points more, and the reading names row 55 as 100% of the gap; productivity: inconsistent measurement |
| 7 | Row 29, *Bueiros tubulares — Seg. 1*: actual finish was 05/06/2026 in rev03 and reads 01/06/2026, its baseline date, in rev04 | Cycle: past rewritten, one actual finish |
| 8 | A link added (row 106 after row 94) and one removed (row 127 no longer after row 123) | Cycle: logic |
| 9 | Row 157, *Lançamento das vigas pré-moldadas*: 12 days became 20, not started | Cycle: duration changed on work not started |
| 10 | Row 132, *CBUQ capa de rolamento — Seg. 4*: baseline moved four weeks | Cycle: the reference moved; warning about the comparison basis |
| 11 | Row 57, *Contenção em gabião*, exists only in rev04; *Remanejamento de cercas — Seg. 4* only in rev03 | Cycle: scope, 1 inserted and 1 removed; 0.33 points of movement not explained by progress |
| 12 | Float to the milestone *Liberação ao tráfego — Segmento 3* fell from 13 to 3 days | Cycle: critical path, float lost; forensics names the origin |
| 13 | Project finish went from 04/10/2027 to 25/10/2027, through the viaduct | Cycle: project finish and its driving chain; forensics: origin in the piles, amplified by row 157 |
| 14 | Paving is about two thirds of what remains, and half of the remaining cost falls between December and March | Looking forward: rain exposure, 50% in reserved months, 52% if everything slips thirty days |

Also there without being planted, because a late schedule has them: SPI 0.90, a
baseline execution index of 0.65, and a four-week look-ahead the practised rate does
not reach.

## Opening it in MS Project changes some of this

Project recalculates a schedule when it opens the XML and again when it saves it as
`.mpp`. What it keeps and what it recomputes decide which findings survive.

- **Kept** (items 2, 3, 4, 6, 7, 8, 9, 10, 11): actual dates, percent complete and
  physical percent, links, constraints, durations, baseline dates and deadlines, the
  inserted and removed rows.
- **Depends on the file as exported** (items 5, 12, 13, 14 and the figures in 1):
  forecast dates, total float, the critical flag, the earned-value fields and the
  time-phased baseline cost. After a recalculation they are Project's, not the
  generator's, and may differ by days, most of all around the out-of-sequence activity.

To reproduce the report as described, run the two XML files as they are.

## Regenerating

```
python3 examples/make_exemplo.py
```

Standard library only, deterministic: the same two files, byte for byte. What happened
in each month and each planted problem are declared at the top of the script
(`PERTURB`, `PLANTED`). `python3 skills/cronoaudit/scripts/test_checks.py` checks that
the files are what the generator writes and that every item above is found.
