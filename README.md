# cronoaudit

**Schedule integrity review for construction and infrastructure programmes.** An Agent Skill,
and a runnable method, that audits a schedule and the indicators derived from it —
hunting the failures that produce a plausible wrong number rather than an error.

From the scheduling tool's own XML export, with nothing installed beyond Python:

- the **nine integrity checks** with stable codes — network first, then dates, then reporting;
- the **S-curve read from the file's own phasing**, reconciled task by task against its totals,
  and earned value reconciled to the cent against the tool's own;
- **productivity and trend by resource** from native assignment quantities: three rates, four
  dates, three verdicts — reprogram, float absorbs, or enters the critical path on a date;
- the **fourteen network-quality metrics** with quoted thresholds, labelled as implementation;
- **Earned Schedule**, look-ahead, pace by group, milestone bands, rainy-season exposure;
- **forensics** that name the activity where each milestone's delay entered;
- a **cycle comparison** between two snapshots: execution, replan, or a moved reference.

One self-contained HTML report in the schedule's own language (English or Portuguese), every
section opening with a rule-built reading, plus a JSON sidecar per analysis. Works with any
agent that reads the open [Agent Skills](https://agentskills.io) format — and with no agent at
all.

## Install

One command installs the skill for every supported agent at once — Claude Code, Codex, Gemini
CLI, Cursor, GitHub Copilot, VS Code, OpenCode — by placing it in the two directories they
read between them.

**macOS / Linux**

```
curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
```

**Windows (PowerShell)**

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
```

`irm` exists only inside PowerShell. Pasted into the Command Prompt (cmd) it answers
*'irm' is not recognized* (*'irm' não é reconhecido*). From cmd, use this line instead:

```
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex"
```

Then restart your agent and ask it to review a schedule.

**Python.** The skill needs Python 3.9 or later and nothing else. On macOS and Linux the
installer uses the one on the machine and stops if there is none. On Windows it looks for a
Python that actually runs (`py -3`, `python`, `python3`, each one executed, because on a
Windows without Python those names are Microsoft Store shortcuts that exist and do nothing).
If none runs, it brings its own: the official CPython 3.13.17 *embeddable package* from
python.org, checked against a SHA-256 pinned in the installer before it is unpacked, placed
in `%LOCALAPPDATA%\cronoaudit\python`. No administrator rights, no registry entry, no PATH
change; deleting that folder removes it. It is used only by cronoaudit.

| Before running the Windows installer | Effect |
|---|---|
| `$env:CRONOAUDIT_NO_PYTHON = "1"` | never download Python; stop with a message if none is found |
| `$env:CRONOAUDIT_EMBED_PYTHON = "1"` | use the bundled Python even when the machine has one |

**Network access, all of it.** The installer downloads this repository's zip from GitHub and,
on Windows only when no working Python is found (or when asked), the Python package from
python.org. Nothing else is fetched and nothing is sent anywhere. The skill itself never
touches the network.

The bundled Python is the standard library only. That is everything the skill needs; the one
thing it cannot do is the optional direct reading of `.mpp` files, which needs a library and
a Java runtime. Export to XML, as the skill recommends anyway.

The Windows installer's Python detection and download have not yet been exercised end to end
on a Windows machine; if it misbehaves, the `git clone` route below works everywhere.

### Or use your agent's own installer

| Agent | Command |
|---|---|
| Any Agent Skills client | `npx skills add Holiv/cronoaudit -g` |
| Claude Code, as a plugin | `/plugin marketplace add Holiv/cronoaudit` then `/plugin install cronoaudit@cronoaudit` |
| Gemini CLI | `gemini skills install https://github.com/Holiv/cronoaudit.git` |
| Codex | `$skill-installer https://github.com/Holiv/cronoaudit` |
| Cursor | Customize → Remote Rule (GitHub) → `https://github.com/Holiv/cronoaudit` |
| A team, through the project | `git clone https://github.com/Holiv/cronoaudit .claude/skills/cronoaudit` inside the project |
| Just the tool, no agent | `git clone https://github.com/Holiv/cronoaudit` and run `skills/cronoaudit/scripts/review.py` |

Where the skill lands: `~/.claude/skills/cronoaudit` (Claude Code, OpenCode, Cursor) and
`~/.agents/skills/cronoaudit` (Codex, Gemini CLI, Cursor, Copilot, VS Code, OpenCode). Pass
`--only claude` or `--only agents` to the installer to choose one.

## Use

```
python3 ~/.claude/skills/cronoaudit/scripts/review.py delivery.xml
python3 ~/.claude/skills/cronoaudit/scripts/review.py previous.xml current.xml
python3 ~/.claude/skills/cronoaudit/scripts/review.py delivery.xml --profile profile.json --group-by DISCIPLINE
```

Export the schedule first: **MS Project → File → Save As → XML Format**. That is the tool's own
documented format; nothing the skill needs is lost in it. Inside an agent, just ask: *review this
schedule*, *compare these two versions*, *customise the organisation profile*.

The whole process, the report section by section, and the judgement the tool cannot make for
you: [`skills/cronoaudit/references/usage.md`](skills/cronoaudit/references/usage.md).

## Manual

A complete technical manual, written for someone who receives a schedule and has to say whether
it is true. Fourteen chapters: concepts from scratch, installation, the report section by section,
the nine checks, network quality, productivity, forecast and forensics, cycle comparison, profile,
the JSON files, limits and labels, FAQ and a bilingual glossary. Every example uses the synthetic
fixtures.

- Português: [`docs/manual/manual-pt.pdf`](docs/manual/manual-pt.pdf)
- English: [`docs/manual/manual-en.pdf`](docs/manual/manual-en.pdf)

Rebuild from source with `python3 docs/manual/build.py` and `node docs/manual/topdf.js` (needs
`puppeteer-core` and a local Chrome).

## What it does not do

It does not read Primavera P6 (the method transfers; nothing was measured there). It does not
produce a contractual delay claim (the forensics reconstruct the mechanism; a claim needs
contemporaneous records and a formal method). It does not certify against DCMA (the fourteen
metrics are implemented and labelled as such). It never invents a distribution, a default, or
a number a file did not carry — and it says `measured`, `inferred` or `reported` on every claim.

## Repository layout

| Path | Role |
|---|---|
| `skills/cronoaudit/` | the skill: `SKILL.md`, `scripts/`, `references/`, `templates/`, `fixtures/` |
| `install.sh` · `install.ps1` | the one-command installers |
| `.claude-plugin/` | manifests for the Claude Code plugin route |
| `sync-local.sh` | maintainer's one-way sync from this repository into the local skill directories |

Verify the tool before trusting a clean result: `python3 skills/cronoaudit/scripts/test_checks.py`.
Every check must fire on the positive fixture and stay silent on the negative one.

## Provenance

Written from a documented, generic method, not ported from any application's source, and
measured on a real 6,484-task programme with 107 calendars. Numbers of scale stay; identities
go: no employer, contractor, contract, chainage, person or value appears anywhere in this
repository.

## Licence

Apache 2.0. © 2026 Helton da Silva de Oliveira.
