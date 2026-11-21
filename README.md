# cronoaudit

**An Agent Skill for reviewing construction and infrastructure schedules.** You hand a schedule
to your agent (Claude Code, Codex, GitHub Copilot, Gemini CLI, Cursor); through the skill the
agent reads it, tells you what deserves attention, answers what you ask, and customises the
report when you want it different. It hunts the failures that produce a plausible wrong number
rather than an error.

The numbers do not come from the agent. They come from the skill's **engine**: a set of Python
scripts that read the scheduling tool's own XML export and compute every figure the same way
every time, so the agent quotes measurements instead of inventing them. The engine also runs
on its own, with no agent, and writes the same report; that is the fallback, not the point.

What the engine measures, from the XML export and with nothing installed beyond Python:

- the **nine integrity checks** with stable codes — network first, then dates, then reporting;
- the **S-curve read from the file's own phasing**, reconciled task by task against its totals,
  and earned value reconciled to the cent against the tool's own;
- **productivity and trend by resource** from native assignment quantities: three rates, four
  dates, three verdicts — reprogram, float absorbs, or enters the critical path on a date;
- the **fourteen network-quality metrics** with quoted thresholds, labelled as implementation;
- **Earned Schedule**, look-ahead, pace by group, milestone bands, rainy-season exposure;
- **forensics** that name the activity where each milestone's delay entered;
- a **cycle comparison** between two versions: what changed in the schedule itself (finish,
  critical path, logic, durations, a rewritten past, network quality) and what moved by
  execution, by replanning, or because the reference moved.

One self-contained HTML report in the schedule's own language (English or Portuguese), every
section opening with a rule-built reading, plus a JSON sidecar per analysis. When an input a
reading needs is not in the file, the report says so instead of reading a zero. The skill
follows the open [Agent Skills](https://agentskills.io) format.

## Where your data goes

- **The engine runs on your machine and sends nothing.** It never touches the network.
- **The installer downloads** this repository's zip from GitHub and, on Windows only when no
  working Python is found (or when asked), the Python package from python.org. Nothing else.
- **The agent is a different matter.** When an agent reads the XML or the report, that content
  goes to the agent's provider, under the terms of your account or your company's. Check the
  company policy before pointing an agent at a contract schedule.
- If the policy forbids it, run the engine without an agent (see [Use](#use)): same report, no
  conversation, nothing leaves the machine. A private mode for the agent is in development.

## Install

One command installs the skill for every supported agent at once — Claude Code, Codex, Gemini
CLI, Cursor, GitHub Copilot, VS Code, OpenCode — by placing it in the two directories they
read between them.

**macOS / Linux**

```
curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
```

**Windows** — the command depends on the window you are typing in:

| In PowerShell | In cmd (Command Prompt) |
|---|---|
| `irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 \| iex` | `powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 \| iex"` |

`irm` exists only inside PowerShell: pasted into cmd it answers *'irm' is not recognized*
(*'irm' não é reconhecido*). Copy the commands from the blocks below, without the table's
escaping:

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
```

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
change; deleting that folder removes it. It is used only by cronoaudit. The Windows installer
has been run on two machines, one with a system Python and one with the bundled one.

**Options for the Windows installer** are environment variables, set in the same window before
the install command. The syntax is different in each shell, and the wrong one is silently
ignored: `set X=1` typed in PowerShell sets nothing the installer can see.

| Option | In PowerShell | In cmd |
|---|---|---|
| Never download Python; stop if none is found | `$env:CRONOAUDIT_NO_PYTHON="1"` | `set CRONOAUDIT_NO_PYTHON=1` |
| Use the bundled Python even when the machine has one | `$env:CRONOAUDIT_EMBED_PYTHON="1"` | `set CRONOAUDIT_EMBED_PYTHON=1` |
| Install from another branch (default `main`) | `$env:CRONOAUDIT_REF="branch-name"` | `set CRONOAUDIT_REF=branch-name` |

To undo one: `Remove-Item Env:CRONOAUDIT_REF` in PowerShell, `set CRONOAUDIT_REF=` in cmd.

The bundled Python is the standard library only. That is everything the skill needs; the one
thing it cannot do is the optional direct reading of `.mpp` files, which needs a library and
a Java runtime. Export to XML, as the skill recommends anyway.

**MS Project add-in (Windows, beta).** A small VBA module adds buttons to Project that export
the open schedule to XML and open a terminal with the skill already started on it, or run the
engine alone where AI is not allowed. It is a shortcut, not a requirement. Files and
instructions: [`msproject/`](msproject/) ([Português](msproject/LEIA-ME.md)).

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

The three commands above are the engine on its own: no agent, nothing leaves the machine.

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
