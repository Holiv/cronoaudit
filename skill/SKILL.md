---
name: schedule-integrity
description: Review a delivered construction or infrastructure schedule, compare it with the previous version, and audit the progress and earned-value figures derived from it - finding the failures that produce a plausible wrong number rather than an error. Use for schedule critical analysis of a contractor delivery, the periodic cycle report, computing or reconciling earned value (BCWS/BCWP/SPI/CPI), S-curves and Earned Schedule, productivity and trend by resource, network quality (DCMA-style metrics), delay forensics by driving path, look-ahead and forecasting, comparing two schedule versions, reading a .mpp or MPXJ-parsed schedule programmatically, or explaining why a control indicator disagrees with its source tool. Runs from one command over the schedule tool's own XML export with no dependency beyond Python, in the schedule's own language, and produces a self-contained HTML report with every section opening with a rule-built reading. Also use when asked to customise the organisation profile or the report ("personalizar padrão da empresa", "personalizar relatório").
user-invocable: true
---

# Schedule integrity review

A method, and a runnable implementation of it, for auditing a schedule and the indicators
derived from it. It targets one failure class specifically: **the calculation is arithmetically
correct, every input is correct in its own source, the result is plausible, nothing raises an
error, and the number is meaningless.** Textbooks cover how to compute earned value. This
covers what goes wrong silently when you compute it on a real delivered file.

## Run it

Export the schedule once from the tool (`File > Save As > XML Format`), then:

```
python3 scripts/review.py delivery.xml                       # review one delivery
python3 scripts/review.py previous.xml current.xml           # the periodic cycle
python3 scripts/review.py delivery.xml --profile profile.json --group-by DISCIPLINA
```

Nothing to install beyond Python. Out come one self-contained HTML report in the schedule's
own language and one JSON sidecar per analysis. Verify the tool itself first:
`python3 scripts/test_checks.py`. The whole process, flags, failure messages and the judgement
the tool cannot make for you: `references/usage.md`.

## The one question, before anything

> **Are all the inputs to this calculation measured against the same reference?**

Four references: **which baseline · which instant · which population · which unit.** Two
inputs disagreeing on any one produce a meaningless result with an impeccable appearance, and
the blame migrates onto the works rather than the calculation. The case family and how to
recognise the fifth: `references/datum.md`.

## What the report contains, in the order it is read

| Section | Answers | Reference |
|---|---|---|
| Verdict and findings A1–P | Does the logic hold? Which dates elapsed, moved, or are misreported? | `checks.md`, `network-rules.md` |
| V0 S-curve | Where the contract should be, where it is, and whether the skill's number matches the tool's | `earned-value.md` |
| V1 progress by group | Did the progress happen where the money is? | `usage.md` |
| V6 productivity | At three rates, when does each activity in progress finish, and does it enter the critical path? | `productivity.md` |
| V7 network quality | Does the schedule hold up as a model at all? Fourteen metrics, quoted thresholds, labelled as implementation | `network-quality.md` |
| V8 looking forward | Earned Schedule with its limits, look-ahead, pace by group, milestone bands, rain exposure | `forecast.md` |
| V9 forensics | Where each milestone's delay entered, by which path; calendars in the wrong year; execution pattern | `forensics.md` |
| Cycle comparison | What moved since last time: execution, replan, or the reference itself | `comparing-versions.md` |

Every section opens with a **Reading**: sentences built by rule from its own figures. Every
finding carries a stable code, problem, impact, solution, and **how to reproduce it** in the
scheduling tool, with the activities collapsed under a toggle. Only the visible row number
identifies an activity.

## Rules the implementation never breaks

- **Network first.** When the tool recalculates over a violated network, every forecast date
  is derived from logic the works does not follow. A1 and A2 gate everything.
- **The conversion basis is per activity.** Working time on each activity's own calendar,
  never the header's day, never a five-day week. A real programme had 107 calendars; counting
  Monday to Friday flagged 27% of it as inconsistent, the calendar brought it to 2%.
- **A pending record is not a network breach.** 100% physical with no actual finish migrates to
  P, so a reporting problem is not reported as an execution problem.
- **Derive from what the file already carries.** The planned curve is the file's own phasing,
  reconciled task by task; earned value is reconciled against the file's own BCWP to the cent.
- **Counting convention is part of the finding.** Three counts for network findings; align with
  whatever the other party's tool shows.
- **Provenance travels with every claim**: `measured`, `inferred`, `reported`. Never promote.
- **A plausible default returned instead of null disarms the check that would exist.** Test for
  a value known to differ, not for non-null.

## Write the executive synthesis when you run it

After `review.py`, read the JSON sidecars and write four to six short paragraphs a director can
read in two minutes: whether the network holds and what that means; where the weight is and
whether progress happened there; the Earned Schedule reading with its limit; the activities the
forensics name; what the next four weeks demand. Quote figures from the files, say what is
`inferred`, add nothing the files do not support. Then:

```
python3 scripts/inject_narrative.py <name>-review.html synthesis.txt --who "Claude, via the skill"
```

## Customising: two conversational flows

The skill runs ready-to-use with no profile. A profile only narrows, and it is written by
`scripts/profile_tool.py`, never by hand. Both flows start by **showing the person what the
file has**, because recognition is reliable and recall is not.

**"Customise the organisation profile" · "Personalizar padrão da empresa".** Run
`python3 scripts/parse_mspdi.py <xml> -o model.json` then
`python3 scripts/profile_tool.py discover model.json`, and show the candidates. Then ask, one at
a time, only what the file could not settle: which field is the discipline, the section, the
justification, the contracted productivity; whether the earned-value method the file declares is
the one the organisation practises; whether B (milestones without deadline) and F (in progress
at zero) should count as findings; the threshold in working days; which baseline slot, if the
elected one is wrong. Write each answer with `profile_tool.py set profile.json key=value`, then
`profile_tool.py show profile.json model.json` to confirm every field resolved. A declared field
the file does not have is reported, never silently ignored.

**"Customise the report" · "Personalizar relatório".** Ask for the accent colour, the three
severity colours, the display and body font stacks, a short label for the header, the language
if it should not follow the schedule, and which sections to hide. Write them under `theme.*`,
`lang` and `sections_hidden`. For deeper changes, copy `templates/report.html` to
`templates/report.custom.html`; it takes precedence and survives updates.

`python3 scripts/profile_tool.py example` prints a filled example. The full key list and what
each does: `references/profile.md`.

## Scope, honestly

Measured on **MS Project** XML exports. **Primavera P6 is not covered**; the optional reader can
convert a P6 file, and the method transfers, but nothing was measured there. Forensic delay
claims and DCMA certification are adjacent and not included; the forensics reconstruct the
mechanism and the network metrics are an implementation of the fourteen, labelled as such.

## Before anything leaves the machine

Never carry over: employer or contractor names, contract numbers, chainages, person names,
contract or works values, local paths. **The figure stays, the identity goes.** An
organisation's standard does not belong in the generic method; what transfers is that the
mapping can be declared rather than coded.
