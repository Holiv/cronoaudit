---
name: cronoaudit
description: Review a construction or infrastructure schedule (received from another party, produced in-house, or under maintenance), compare it with the previous version, and audit the progress and earned-value figures derived from it, finding the failures that produce a plausible wrong number rather than an error. Use for the critical analysis of a schedule delivery, the periodic cycle report, earned value (BCWS/BCWP/SPI/CPI), S-curves and Earned Schedule, productivity by resource, network quality (DCMA-style), delay forensics by driving path, look-ahead, comparing two versions, reading a .mpp or MS Project XML, or explaining why an indicator disagrees with its source tool. Runs locally from one command, with no dependency beyond Python, and writes a self-contained HTML report in the schedule's language. Also for customising the organisation profile or the report ("personalizar padrão da empresa", "personalizar relatório").
user-invocable: true
---

# cronoaudit — schedule integrity review

A method, and a runnable implementation of it, for auditing a schedule and the indicators
derived from it. It targets one failure class specifically: **the calculation is arithmetically
correct, every input is correct in its own source, the result is plausible, nothing raises an
error, and the number is meaningless.** Textbooks cover how to compute earned value. This
covers what goes wrong silently when you compute it on a real file.

## Run it

Export the schedule once from the tool (`File > Save As > XML Format`), then:

```
S=~/.claude/skills/cronoaudit/scripts          # or ~/.agents/skills/cronoaudit/scripts
python3 $S/review.py delivery.xml                       # review one delivery
python3 $S/review.py previous.xml current.xml           # the periodic cycle
python3 $S/review.py Rev04.mpp                          # Windows: exported through MS Project itself
python3 $S/review.py --from-project                     # Windows: the schedule open in MS Project
python3 $S/review.py Rev03.mpp --from-project           # Rev03 against the one open in Project
python3 $S/review.py delivery.xml --profile profile.json --group-by DISCIPLINA
python3 $S/review.py delivery.xml --outdir reports --lang pt
python3 $S/review.py --config                           # the stored mode preference
python3 $S/review.py delivery.xml --secret              # secret mode: run by the PERSON
```

Settle the mode first: see "Modes: free and secret" below.

On Windows the interpreter is `python` (or `py`), not `python3`: there `python3` is often a
Store shortcut that runs nothing. Use whichever answers `--version`, and write that name in
every command you give the person.

Always call the scripts by their absolute path; the person's working directory is wherever
the schedule is, not the skill's folder. Nothing to install beyond Python. Out come one
self-contained HTML report in the schedule's own language and the JSON sidecars: `-review`,
`-scurve`, `-productivity`, `-quality`, `-forecast`, `-forensics`, `-readings`; with two files, also `-cycle` and `-cycle-readings`. Reports and sidecars name files, never folders. The self-test
`python3 $S/test_checks.py` proves the installation once; it is not part of every
conversation. The whole process, flags, failure messages and the judgement the tool cannot
make for you: `references/usage.md`.

## Modes: free and secret

**Settle this before reading any schedule data and before running the engine.** That means
before opening an XML, a report or a JSON sidecar, and before quoting anything from one.

- **Free mode.** You read the schedule and the results, and whatever you read goes to your
  provider, under the person's or the company's account.
- **Secret mode.** You never see the schedule. The person runs the engine
  on their own machine; it writes the real report into a local vault and a **coded copy**
  into a work folder, and you are started inside that folder. Names are tokens (`T·3fa91c`),
  money is multiplied by a secret factor, dates are day counts from a secret origin
  (`D+0412`; `d+0412` is the same day in display form, `M+0013` a month, `Y+0001` a
  year). Durations, percentages, counts, SPI/CPI and every ratio, row IDs and WBS codes
  stay real. The monthly rain-reserve series is withheld (it would tell the season).

1. **Are you inside a secret work folder?** If the working directory holds
   `cronoaudit-secret.json`, this is a secret session: go to "In a secret session" below.
   Do not ask the mode question.
2. **Did the person ask for secret?** If the request carries `--secreto` or `--secret`, or
   asks for secret or private mode in any words, **do not take the XML path and do not run
   the engine yourself**: an agent that holds the original protects nothing. Tell the
   person to run, in their own terminal (not through you):

   ```
   python3 <absolute path of the scripts>/review.py <their file>.xml --secret
   python3 <absolute path of the scripts>/review.py previous.xml current.xml --secret
   ```

   It prints a work folder; they start you again inside it (`cd <folder>` then the agent).
   Started by Claude Code, the engine refuses secret mode by itself (exit 3).
3. **Otherwise read the stored preference** with `python3 $S/review.py --config`. It reads only
   the preference file, never a schedule, and its first line is `secret: ask`, `secret: on` or
   `secret: off`.
   - `off`: go on in free mode. Do not ask.
   - `on`: treat it as a request for secret mode, as in step 2.
   - `ask`: ask the person this, in their language, **before reading anything**:

     > Modo LIVRE: o que o agente ler vai para o provedor dele. Continuar? [s] livre / [secreto] / [nunca] não perguntar mais

     > FREE mode: whatever the agent reads goes to its provider. Continue? [y] free / [secret] / [never] do not ask again

     "s" or "y": free mode, this time. "secreto" or "secret": step 2. "nunca" or "never": run
     `python3 $S/review.py --secret off`, tell the person it can be undone with
     `--secret ask`, and go on in free mode. Any other answer is not a yes: ask again.
   - If the command fails, or says the file could not be read, treat it as `ask` and say so.
4. **In free mode, pass `--free` to the engine.** The mode is already settled, so the engine
   neither repeats the question nor stops.
5. **A request written by the MS Project add-in** (`pedido.md`) states the mode: there the
   person was asked by the add-in before you were started. Do not ask again.

### In a secret session

- **Say this first, in the person's language:** "Secret mode. Refer to
  activities by code or by row ID: anything you type with a real name or value goes to the
  AI service."
- Read only the files in the folder; `cronoaudit-secret.json` lists them, the code shapes
  and which JSON keys are money. Never ask for, look for or open the original, and never
  run `review.py`. Write commands with full paths and no shell variables: the guard
  blocks variables.
- Quote tokens and codes exactly. Write coded money with its mark, in the report's notation
  (`¤1.234.567`); a figure without the mark is not decoded. A date you write as `D+0412`
  comes back as a real date.
- **What secret mode answers:** logic, float, critical path, durations, progress, cost
  proportions and weights, deltas between versions, network quality, deviations and
  inconsistencies, the forensics chain by row ID. **What it does not:** real values, company,
  supplier or person names, locations, and absolute dates ("does this fall before the March
  contractual milestone?"). Refuse those plainly and point to the way out: the decoded
  report on the person's machine, the person's own `secret_decode.py text`, or free mode.
- **The synthesis only when asked**, as in free mode. After your first reading, offer in one
  line the synthesis and the report with real names; do not write either unasked. Asked for
  the synthesis: write it in codes, inject it with `inject_narrative.py` into
  `schedule-review.html`, or `previous--to--current-cycle.html` for a cycle (where free mode
  puts it too), then run `python3 <scripts>/secret_decode.py finish`. Asked only for the
  report: run `finish` without a synthesis. It decodes on this machine, beside the original,
  opens the report, and prints counts only.
- **Another version, or a comparison, is a new coded run started by the person.** Point to the
  MS Project tab (Comparar versões, answering Yes to secret mode) or to the `review.py ... --secret`
  command they run in their own terminal; then they open you in the new work folder.
- **Never run `secret_decode.py text`.** It prints real names, so its output would go to
  your provider. It is the person's command, typed in their own terminal, to read one of
  your answers with real names (it refuses inside Claude Code, and the guard blocks it).
  When you point the person to it, write it whole, with the absolute path of the scripts
  and of this folder, no `~` and no variables (Windows PowerShell does not expand `~` for
  Python), and `python` on Windows: `python C:/.../scripts/secret_decode.py text "C:/.../<this
  folder>"`. Then: paste, and on a line of its own Ctrl-Z Enter (Windows) or Ctrl-D.

**Be plain about what protects what.** The mode question is you following this skill, not
an enforcement. What code enforces: the engine refuses secret mode when Claude Code started
it; the work folder holds only coded files (a leak test proves it on every test run); and,
**for Claude Code only**, the folder carries deny rules and a hook that let a session read
only its own folder, run only the finishing scripts and use only the tools a secret session
needs: PowerShell, connectors, Artifact, SendUserFile, SendMessage and any tool not on its
list are closed. The hook is a tripwire, not a
sandbox. **For Copilot CLI and Codex nothing is enforced**: the folder carries
the same rules as instructions only. Coding lowers what leaves the machine; it does not
make the structure, durations and row IDs anonymous, and it does not replace the company's
own policy on AI services. If the person asks whether their data is protected, say exactly
this.

## How a conversation starts

The person may be on any side of the schedule: the one who received it, the one who produced
it, the one responsible for updating it, a regulator, or someone studying. Never assume a role.

0. **Before reading any file or sidecar, say where the data goes**, once, in a first
   conversation. What you read (the XML, the reports, the JSON) is sent to your provider under
   the person's or the company's account; the engine itself runs locally and sends nothing, and
   it runs without an agent with the same report. This step is where the person chooses how to
   proceed; any other mode of running is offered here, from its own section.
1. **Locate the file.** If the request names a path, use it. If it names a folder, or nothing,
   look in that folder (or the working directory) only, not in subfolders, for schedules
   (`.mpp` and `.xml`; when both exist for the same name, take the `.mpp`, which is the
   original): exactly one, use it and name it in the reply; more than one, list them and ask
   which, offering the cycle comparison when two look like versions of the same schedule;
   none, ask for the path, or offer `--from-project` if the person has it open in MS Project.
   Never pick silently among several. Never list the person's home folders (Documents,
   Desktop, Downloads) or offer files that are not schedules.
   **A `.mpp` needs nothing from the person on Windows**: pass it to `review.py` as it is, and
   the engine exports it through the MS Project installed on the machine (read-only; the file
   is not changed). Do not ask for an XML and do not explain XML unless the export fails; its
   message says what to do. "The one I have open" is `--from-project`. A schedule open in
   Project is never touched: the file as saved on disk is copied and the copy exported, so
   changes not yet saved are not in the analysis (the engine prints a note; tell the person). Off Windows, a `.mpp`
   still needs the XML export, done in Project by whoever has it.
2. **Run the analysis once.** `review.py <file> --free` writes the report and the JSON sidecars beside
   the XML; `--outdir <folder>` when the person names a folder (it is created if missing,
   relative to the working directory). The analysis and the report are the same command, so
   the report always exists after the first run.
3. **Language.** The report follows the schedule. When the detection says `confidence: low`
   (too little text to judge), run with `--lang` in the language the person writes, and say
   so. Never leave a low-confidence default unmentioned.
4. **State the full path of the report in the first reply**, then read the sidecars in the
   report's own order: blocking notices, `conventions`, `counts` (network first), scurve
   totals and reconciliation, quality metrics that fail, forecast, forensics, productivity
   verdicts. After a cycle run, read `-cycle-readings.json` and `-cycle.json` in this order:
   warnings (rewritten past first), C1 finish, C5 rewritten past, the residue and its named
   terms, C3 and C4 with P2 (replan against execution), P1, C2, C6. The `-readings.json` sidecar
   holds the rule-built sentences the report shows; quote those rather than composing your own.
   Do not rerun unless asked or the file changed.
5. **Counts.** The `counts` block of `-review.json` is the official figure (distinct
   activities, as successors, as predecessors); the `findings` lists carry one row per link
   end and are longer by design.
6. **The report need not be opened.** A conversation about one finding, one rate or one
   milestone is a complete use of the skill. Write the executive synthesis only when asked, or
   when the person asks for a report to hand over. After a cycle run, offer both in one line:
   the synthesis, and the list of what to demand from the other party. The engine builds that
   list: `demands` in `<prev>--to--<curr>-cycle-readings.json`, also the last section of the
   cycle report. Quote it; add to it only what the person brings, and say so.

## How to speak about the results

The engine measures; you read, explain and answer. Keep the two apart.

- **Every number comes from the engine's files.** Never compute, estimate or round one on your
  own account. If a figure is not in the files, say it is not there.
- **Present numbers rounded**: percentages and percentage points with two decimals ("35,56%",
  not "35,5556%"), in the language's own notation. The JSON keeps full precision; that is for
  machines.
- **Name the baseline the way the tool does**: "Baseline" or "Baseline 1" ("linha de base",
  "linha de base 1"). Never the storage word for where it is kept: no "slot", and in Portuguese
  never "gaveta". `baseline_slot` is a key in the JSON, not a word for a person.
- **Explain jargon the first time it appears.** "Population" is the set of activities a figure
  was counted over; "leaf" is an activity that is not a summary row; a "reading" is a sentence
  the engine built by rule from its own figures. Do not assume the person knows these.
- **When an automatic reading contradicts the data, say so and show the data.** The readings
  are built by rule and a rule can be wrong for a file it did not foresee. Check each one you
  quote against the figures beside it; if they disagree, quote the reading, state the figures,
  and say which you believe and why. A reading stated without the input it needs is the very
  failure this skill hunts.
- **Mark deductions.** What the files state is `measured`; what you conclude from them is
  `inferred`, and you say so in the sentence ("inferred: ..." / "inferência: ..."). Before
  writing one, check whether a sidecar already holds the figure (`residual_terms`,
  `unmatched.removed` with its percent, `past_rewritten`). An inference the engine could have
  measured is an engine gap: say so.

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
| Cycle comparison | What changed in the schedule itself (finish, critical path, logic, durations, rewritten past, network quality) and what moved: execution, replan, or the reference | `comparing-versions.md` |

Every section opens with a **Reading**: sentences built by rule from its own figures. Every
finding carries a stable code, problem, impact, solution, and **how to reproduce it** in the
scheduling tool, with the activities collapsed under a toggle. Only the visible row number
identifies an activity.

## Rules the implementation never breaks

- **Network first.** When the tool recalculates over a violated network, every forecast date
  is derived from logic the works does not follow. A1 and A2 gate everything; one to three
  pairs off the critical and finish chains are named with the milestones they reach, not read
  as a broken network (`references/checks.md`).
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
- **A reading is stated only when its input exists.** No links: "the network holds" is not said.
  No earned value in the file: nothing is reconciled, and zero against zero is never a match.
  Baseline cost not distributed in time: planned-to-date is unavailable, not zero. No reserved
  period on any calendar: weather exposure is unread, not nil. The `inputs` block of
  `-readings.json` and of `-scurve.json` says what the file has.

## Writing the executive synthesis, when asked

Read the JSON sidecars and write four to six short paragraphs a director can
read in two minutes: whether the network holds and what that means; where the weight is and
whether progress happened there; the Earned Schedule reading with its limit; the activities the
forensics name; what the next four weeks demand. For a cycle: the finish and milestones against
their deadlines; the integrity of the measurement (rewritten past, moved baseline, the residue
by its terms); replan against execution; what to demand from the other party (the engine's
`demands` list). Quote figures
from the files, say what is `inferred`, add nothing the files do not support. Then:

```
python3 $S/inject_narrative.py <name>-review.html synthesis.txt --who "Claude, via the skill"
python3 $S/inject_narrative.py <prev>--to--<curr>-cycle.html synthesis.txt --who "Claude, via the skill"
```

## Customising: two conversational flows

The skill runs ready-to-use with no profile. A profile only narrows, and it is written by
`scripts/profile_tool.py`, never by hand. Both flows start by **showing the person what the
file has**, because recognition is reliable and recall is not.

**"Customise the organisation profile" · "Personalizar padrão da empresa".** Run
`python3 $S/parse_mspdi.py <xml> -o model.json` then
`python3 $S/profile_tool.py discover model.json`, and show the candidates. Then ask, one at
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
`templates/report.custom.html`; it takes precedence. An update replaces the whole skill folder,
so keep the copy outside it too and point to it with `--template` or the profile's `template` key.

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
