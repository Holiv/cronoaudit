# How to use this: the whole process, start to finish

## What you need

**Python 3.9 or later. Nothing else.** No library to install, no Java, no network, no account.
The scripts are stdlib-only on purpose: a tool that needs a dependency resolved before it
answers anything does not get used by the person who received a schedule this morning.

## Step 1 — get the schedule out of the tool (about fifteen seconds)

A `.mpp` file is a proprietary binary. Nothing outside Project reads it without a dedicated
library, so there is one small export step, and it is the only manual work in the process:

> **In MS Project: File → Save As → choose "XML Format (\*.xml)".**

That is Project's own documented interchange format. It carries the tasks, the predecessor
links with their lags, all eleven baseline slots, the calendars, the custom fields and the
status date — **nothing this skill needs is lost in the export.**

Ask the contractor to send the XML alongside the `.mpp` and the step disappears entirely from
your week. It is one extra click in their Save As dialog.

*Optional, if you would rather not export at all:* with `pip install mpxj` and a Java runtime
available, the scripts read `.mpp` directly, and Primavera P6 XER and P6 XML come in through
the same library. Treat a P6 result as unverified — the checks here were measured against MS
Project files, not P6.

## Step 2 — run one command

**Reviewing one delivery:**

```
python3 scripts/review.py delivery.xml
```

**The periodic cycle, comparing against last time:**

```
python3 scripts/review.py previous.xml current.xml
```

With two files the earlier one is the previous snapshot. You get the cycle comparison **and** a
review of the current file, deliberately: comparing two files that do not each hold together is
comparing two wrong answers.

Useful flags: `--outdir` to choose where the output lands, `--threshold-days` to move the 30-day
threshold for the pulled-forward and delayed checks, `--tolerance-days` for the duration
thermometer, `--quiet` to write the files without the console summary.

## Step 3 — read what comes out

Four files per run, written next to the input:

| File | What it is for |
|---|---|
| `<name>-review.html` | the report you attach to the meeting record or print to PDF |
| `<name>-review.json` | every finding as data, for a spreadsheet or your own dashboard |
| `<a>--to--<b>-cycle.html` | the cycle report, when you passed two files |
| `<a>--to--<b>-cycle.json` | the same as data |

The HTML has **no external references at all** — no CDN, no web font, no image host. It opens
from a network share, from an email attachment, from a laptop with no connection, and it looks
the same in five years. One button prints it to PDF, because the artefact that ends up attached
to a meeting record is a PDF, and a report that cannot become one gets screenshotted instead.

### Read it in this order, and the report is laid out to enforce it

1. **The blocking notices, if any.** No status date means every adherence check is measured
   against nothing. No baseline cost means there is no planned half. The run tells you instead
   of quietly substituting today's date.
2. **The network banner.** If activities are involved in violated logic, **stop and settle that
   before discussing a single date.** When the tool recalculates over a network the works does
   not follow, every forecast date in the file is derived from a false premise.
3. **The finding cards**, in the method's three layers: network integrity, then date adherence,
   then reporting consistency.
4. **Each finding's table**, which states the filter that reproduces it.

## Language

**The report follows the schedule.** The language is detected from the file's own text —
activity names, calendar names, the project title — using a function-word and diacritic score,
and the report states which language it chose and how strong the evidence was. A Portuguese
schedule produces a Portuguese report, console summary included, with no flag to set.

Nobody should have to configure this, and a setting would be wrong as often as right: the
person running the review is frequently not the person who wrote the file. Pass `--lang en` or
`--lang pt` to override. English and Portuguese ship today; adding a language means adding one
block to `scripts/i18n.py` and nothing else, because the template holds no prose of its own.

## What each output answers

| Code | Finding | Layer |
|---|---|---|
| A1 | Successor started without the predecessor complete | network |
| A2 | Total inversion: successor complete, predecessor not started | network |
| H | Trend date elapsed with no actual progress | adherence |
| E | Pulled forward beyond the threshold and never started | adherence |
| C | Delayed beyond the threshold | adherence |
| G | Duration disagrees with the start-to-finish window | consistency |
| B | Milestone with no deadline set | consistency |
| F | In progress with percent complete at zero | consistency |
| P | Declared complete with no actual finish | consistency |

From the cycle comparison you additionally get the earned figure for both snapshots, the
movement between them, the per-activity decomposition that sums to that movement, the
**unexplained residue** when it does not, the three-way execution / replan / reference reading,
and the inserted and removed activities.

## The three things that make the output defensible

**Every finding ships with how to reproduce it.** Not "trust me" but "check it yourself": the
report names the filter and lists the row numbers a person can find on their own screen. This is
the difference between a report that carries a meeting and one that starts an argument.

**Every number states its convention.** The threshold and its unit, the baseline slot used and
how it was chosen, the population, the counting convention, and where the percentage came from.
Network findings are counted three defensible ways at once — distinct activities, as successors,
as predecessors — because *"how many activities have the problem"* depends on how you count, and
**diverging from the convention of the tool the other party uses hands them the argument.**

**Both identifiers travel together.** The stable unique identifier is what the data joins on;
the visible row number is the only one a person can see on their screen. A finding list in stable
IDs alone is unusable in a meeting.

## Judgement the tool cannot make for you

- **G is a thermometer, not a finding.** It says something was edited inconsistently, not what.
  Use it to choose what to inspect. Never report it alone.
- **Working days are counted on each activity's own calendar**, read from the activity's
  Calendar column, including that calendar's exceptions. The project calendar is used only for
  activities that have none of their own. This is not a detail: on one real programme 107
  calendars were in use, most activities worked a nine-hour six-day week while the file header
  said eight hours over five days, and a rainy-season calendar carried 616 non-working days of
  weather reserve. Counting Monday to Friday against the header's day flagged 27% of that
  schedule; counting on each activity's calendar flagged 2%, and the real signal stopped being
  buried. **Read the calendar table in the report.** If the shift length or the working week is
  not what the works actually does, every date inherits the error — and a calendar registered
  against the wrong year embeds optimism that nothing else in the file announces.
- **Percent complete may have been typed by a person** rather than derived from work done. When
  it is, it is a declaration, and everything computed from it inherits that. The report says
  which field it used.
- **The prevailing baseline slot is elected from the data**, not read from a field, because the
  field that should declare it is not dependable. The report states the slot and the basis.
  Check it against what the schedule owner believes.

## If something goes wrong

| What you see | What it means |
|---|---|
| `root element is not a Project XML export` | the file is some other XML. Re-export with Save As → XML Format. |
| `No StatusDate in the file` | set a status date in the schedule and export again. The run refuses to guess. |
| `No baseline slot carries leaf cost above zero` | no baseline was saved, or it has no cost. Adherence cannot be computed. |
| every check reports zero on a file you know is troubled | check the population line: summary-only files, or files where everything is marked external, have no leaves to test. |

## Verifying the tool itself before you trust it

```
python3 scripts/test_checks.py
```

Two halves, and the second is the one people skip. On the positive fixture **every check must
fire**. On the negative fixture **every check must stay silent**. Without the second half a clean
result means nothing: a probe that cannot fire reports no findings on a broken file just as
happily as on a sound one. **Prove the instrument can pass before trusting a negative.**

The fixtures are synthetic and live in `fixtures/`, regenerated by `make_fixtures.py`. No real
schedule data anywhere in this skill.

## Provenance of this implementation

The method and its measured findings come from production use. **These scripts are a fresh,
dependency-free implementation of that method** — they are not the production tool, and the
production in-tool implementation is a separate proprietary product that is not distributed here.

Label accordingly: the method statements are `measured` where the reference files say so. The
scripts' behaviour is **verified against synthetic fixtures**, and `inferred` on real-world
exports until you run them on one. Run it on a real export and the label moves — that is how it
is supposed to work.
