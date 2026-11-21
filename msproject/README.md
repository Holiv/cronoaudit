# cronoaudit inside MS Project

cronoaudit is a **skill**: the agent (Claude Code, Codex, GitHub Copilot CLI, Gemini CLI) reads
the schedule through it, talks with the planner, interprets, and customises the report on
request. The Python engine is the skill's instrument: the numbers come from it, so the agent
never invents one.

This VBA module is only the **entry shortcut**. It exports the open schedule to XML and opens a
terminal with the skill already started on it. Everything it does can be done by hand.

Status: **v0.2.** Export by macro, starting a process and finding Python were measured on two
Windows machines with v0.1. Launching the agent from the macro is new and not yet measured.

| Macro | Does | Data leaves the machine? |
|---|---|---|
| `CronoauditAnalisar` | exports the XML, writes `pedido.md` (the request) and opens the agent in that folder with the skill started | **yes**: whatever the agent reads goes to the agent's provider |
| `CronoauditComparar` | asks for the other version (.mpp or .xml), exports both, opens the agent with a comparison request | **yes**, same |
| `CronoauditExportarXml` | exports the XML and opens the folder in Explorer | **no**. Nothing is sent, nothing runs |
| `CronoauditSemIA` | exports, runs the engine, opens the HTML report | **no**. Everything runs locally |
| `CronoauditCompararSemIA` | the same for the comparison of two versions | **no** |
| `CronoauditConfigurar` | agent, reports folder, Python, `review.py`, reset | no |

The add-in itself sends nothing; the agent does, under the terms of the user's or the company's
account. A one-time notice says so on the first use of Analisar or Comparar. Where company
policy forbids AI, the two "SemIA" macros produce the same report with no conversation, and
Analisar and Comparar offer that route when no agent is installed.

## How the agent is started

A visible terminal (`cmd /k`) opens in the run folder with a short ASCII prompt, *"Use the
cronoaudit skill. Read pedido.md in this folder and follow it."* The real request is in
`pedido.md`, written as UTF-8, which keeps accented text off the command line.

| Agent | Launch line | Source for the form |
|---|---|---|
| Claude Code | `claude "PROMPT"` | CLI reference: "Start interactive session with initial prompt" |
| Codex CLI | `codex "PROMPT"` | CLI reference and source: optional `PROMPT` argument of the interactive command |
| GitHub Copilot CLI | `copilot -i "PROMPT"` | CLI command reference: `-i PROMPT`, `--interactive=PROMPT` |
| Gemini CLI | `gemini -i "PROMPT"` | CLI reference: `--prompt-interactive`, `-i` |

By default the first one found on PATH is used, in that order; `CronoauditConfigurar` fixes one.

## Files

- `Cronoaudit.bas`: the add-in module, imported into `Global.MPT`. It never replaces the Global.
- `CronoauditTeste.bas`: the feasibility probe (XML export by macro, which document is active
  afterwards, whether a macro may start a process, whether Python 3.9+ is reachable).
- `LEIA-ME.md`: install, ribbon buttons, the terminal-only route and troubleshooting (Portuguese).

Runs go to `%LOCALAPPDATA%\cronoaudit\relatorios`, outside any synced folder, because the XML and
the report carry project data.

## Install, in short

1. Install the skill with `install.ps1` (main README). It brings its own Python when the machine
   has none.
2. In Project, with no schedule open: `Alt+F11`, select `ProjectGlobal (Global.MPT)`, remove any
   earlier `Cronoaudit` module, `File > Import File...`, choose `Cronoaudit.bas`,
   `Debug > Compile ProjectGlobal`, save.
3. Run a macro with `Alt+F8`, or add ribbon buttons: `File > Options > Customize Ribbon`, new
   tab, choose commands from `Macros`, and add the five working macros in the order of the table.

The terminal-only route stays valid and cross-platform: `File > Save As > XML Format`, open the
agent in that folder and ask it to use the cronoaudit skill; or run `review.py` directly.

The `.bas` files are plain ASCII (a subset of cp1252) with CRLF line endings, because the VBA
editor imports in the machine's ANSI code page. That is why their messages carry no accents.
