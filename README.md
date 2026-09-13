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

Then restart your agent and ask it to review a schedule. Needs Python 3.9 or later. Nothing is
sent anywhere; the only network access is the download. The PowerShell installer was written
to mirror the shell one and has not yet been exercised on a Windows machine; if it misbehaves,
the `git clone` route below works everywhere.

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
