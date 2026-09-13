# Productivity and trend by resource

`measured` on a 6,484-task export with 100 resources and 5,251 assignments, 88 of the
resources material. Nothing here reads a custom field.

## Where the quantities live

For a **material resource, Project stores the quantity in the work fields, as hours of the
ISO duration.** `PT10567H0M0S` on an assignment whose resource is labelled m³ is 10,567 m³;
`PT11H3M0S` on one labelled units is 11.05. Verified against a hand-kept quantity column on
the same file: identical. The same encoding gives:

| Field | Meaning for a material assignment |
|---|---|
| baseline work | planned quantity |
| actual work | executed quantity |
| remaining work | remaining quantity |
| time-phased actual work, block type 2 | executed quantity per day |
| time-phased baseline work, block type 4 | planned quantity per day |

An assignment with resource `-1` is the tool's way of writing "no resource" and cannot be
trended; the report counts them.

## Three rates, not one

One rate is not a fair reading. A cut activity hit by a fortnight of rain shows a rate that
says nothing about the crew.

| Rate | How | What it answers |
|---|---|---|
| own | executed on this activity ÷ working days elapsed since its actual start, on its calendar | what is happening here, weather included |
| global | everything executed for the resource across every front ÷ the working days those assignments took | the fair scenario, diluting a bad fortnight |
| recent | the resource's last 30 days of daily executed blocks ÷ the working days in that window | the rate of now, not the average of months |

The own rate divides by the days **elapsed**, including days with no production. That is the
point: a crew that produced on eight of ten days practised the ten-day rate.

Also computed: the **planned** rate, baseline quantity over the baseline window's working
days, and two **required** rates, remaining quantity over the working days to the trend
finish and to the late finish.

## Four dates, three verdicts

Per activity in progress with quantity remaining, the remaining quantity is run over each of
the three rates, in working days of the activity's own calendar from the status date, and
read against:

| Date | Source |
|---|---|
| trend finish | the schedule's current finish |
| baseline finish | the prevailing baseline slot |
| late finish | the file's own late finish, which already holds the float |
| projected finish | remaining ÷ rate, on the calendar |

| Projected finish lands | Verdict | Meaning |
|---|---|---|
| not after the trend | ahead | nothing to do |
| after the trend, not after the baseline | **reprogram** | the forecast is wrong, the baseline is not threatened |
| after the baseline, not after the late finish | **baseline delay, float absorbs** | no impact on the end date yet; the report says how many days of float remain |
| after the late finish | **enters the critical path** | on the date shown, before the schedule shows it |

The verdict is given for each rate, and the activities are ordered by the global-rate verdict,
gravest first. When own and global disagree by much, that disagreement is itself a finding:
this front is off the resource's pattern.

## Provenance per row

Where the executed quantity was entered, the row is `actual`. Where only a physical percent
was reported, the executed quantity is percent times planned and the row says `inferred` —
validate the fill before trusting a trend, or the trend inherits the hole. On the real file,
executed quantity was entered on 291 of 5,251 assignments.

## What a contracted productivity adds

An organisation may keep a contracted productivity per crew in a custom field. It is an
overlay for comparison, declared through the profile, never a requirement: everything above
runs from native fields alone.
