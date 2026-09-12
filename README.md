# schedule-integrity — a Claude Code skill

A method for auditing an infrastructure schedule and the progress and earned-value figures
derived from it. It targets one failure class: the calculation is correct, every input is
correct in its own source, the result is plausible, nothing raises an error, and the number
is meaningless.

Textbooks cover how to compute earned value. This covers what goes wrong silently when you
compute it on a real delivered file.

## Layout

| Path | Role |
|---|---|
| `skill/` | **canonical.** Edit here. |
| `install.sh` | one-way sync into `~/.claude/skills/schedule-integrity` |

Never edit the installed copy. A correction made downstream is erased by the next sync and
nothing signals it.

## What it does, in one run

    python3 skill/scripts/review.py delivery.xml --group-by DISCIPLINE

From the scheduling tool's own XML export, with nothing installed beyond Python:
the nine integrity checks with stable codes, the S-curve read from the file's own
phasing and reconciled against its totals, productivity and trend by resource from
native assignment quantities, the fourteen network-quality metrics, Earned Schedule
and the look-ahead, and the forensics that name where each milestone's delay
entered. One self-contained HTML report in the schedule's own language, every
section opening with a rule-built reading, plus a JSON sidecar per analysis.

An organisation declares its own conventions in a profile instead of having them
coded: `python3 skill/scripts/profile_tool.py example`.

## Install

    ./install.sh

Skills are enumerated when a session starts, so it becomes active in the next session, not
the current one.

## Provenance

Written from a documented, generic method, not ported from any application's source. Every
factual claim carries a label: `measured`, `inferred` or `reported`. That distinction is the
point — half the value of accumulated knowledge is not having to re-measure, and the promise
only holds if it is clear what was actually measured.

Mechanics were measured on MS Project files. **Primavera P6 is not covered**, and neither is
forensic delay analysis or the DCMA 14-point assessment.

## Publication status

**Private and unpublished, by decision.** Several findings describe defects located in
production systems. As method they are generic and transferable; as public narrative they sit
close to exposing a specific system's failure. Separating the mechanism from the case is easy
but must be a deliberate rewrite, not a side effect of the material moving.

Before anything here is committed to a public remote: no employer or contractor names, no
contract numbers, no chainages, no person names, no contract or works values, no local paths
revealing a folder structure. **The figure stays, the identity goes.**
