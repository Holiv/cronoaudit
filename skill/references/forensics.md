# Forensics of the scenario

Where did the delay come from, by which path, and when did it start? **Not a contractual
delay claim.** Those need contemporaneous records and a formal method (the AACE recommended
practices on forensic schedule analysis). This reconstructs the mechanism from the file's dates,
links and calendars, with reproducible evidence, to sustain the meeting and the notification.
The contractual conversation happens in real time, with each organisation's reality; nothing
of it is pre-generated.

## Driving path per milestone

From each future milestone, walk back through the predecessor that **actually drives** each
start — the one whose link instant plus lag lands latest, on the successor's calendar — until
the chain reaches an activity that has finished (the past drives nothing) or an open end.

Each node carries its finish variance against the baseline in working days. The **origin** is
the deepest node on the chain still carrying at least five working days of variance: walking
from the milestone backwards, variance is inherited from the driver, so the last node that
still has it is where it entered. The delay has a name and a row number, not an aggregate.

Also reported: which activities originate delay on the most milestones — one name can be the
root of a dozen slipped dates — whether each chain reaches started work, and whether it dies
on an open end, which is the Q1 finding seen from the milestone's side.

## Calendar forensics

A productivity reserve registered for one year while the activities on that calendar execute in
another embeds optimism nothing in the file announces: the month gets its full working days
instead of its real ones. Per calendar in use: non-working exceptions per year against
activity-days per year, with two flags — years with activities and no reserve while the
calendar has reserve elsewhere, and years with reserve and no activities.

## Execution pattern

Out-of-sequence execution by the month the successor started, counting both the pairs in the A1
count and the both-complete pairs recorded outside it. And the distribution of start slippage
against the baseline across started activities: P20, P50, P80, how many started early and how
many late.

## With a previous snapshot

- **Float consumed** per activity and per group: total float before minus total float now, in
  working days. Float that disappears while dates hold is delay still invisible.
- **Became critical this cycle**: float above zero before, zero or below now.
- **Milestone movement attributed to the chain**: each milestone's finish movement between the
  snapshots, with what moved on its driving chain read through the comparator's three signals —
  execution, replan, or a moved reference — and the majority reading as the attribution. The
  windows analysis for one window; a series of snapshots extends it across cycles.
