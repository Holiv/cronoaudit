# cronoaudit inside MS Project

cronoaudit is a **skill**: the agent (Claude Code, Codex, GitHub Copilot, Gemini CLI) reads
the schedule through it, talks with the planner, interprets, and customises the report on
request. The Python engine is the skill's instrument: the numbers come from it, so the agent
never invents one.

This VBA module is only the **entry shortcut**. It exports the open schedule to XML and opens a
terminal with the skill already started on it. Everything it does can be done by hand.

## Install with one command (v0.5)

With Project closed, in PowerShell:

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/msproject/install-msproject.ps1 | iex
```

The installer backs up `Global.MPT` and the ribbon file, opens Project, copies the module from the
`cronoaudit.mpt` template into `Global.MPT`, and adds the **Cronoaudit** tab without removing your
other tabs. The person answers two things: **Computer**, if the Logon window asks for a profile,
and **Disable macros**, at the template's warning. No security setting is changed. To remove:
`$env:CRONOAUDIT_MSPROJECT_REMOVE="1"` and the same command.

Tested on Windows on 22/11/2026: installation, the buttons on a freshly opened `.mpp` (no prompt to
save; the export reads a copy of the file as saved on disk), installation over the previous
version (the module is replaced) and removal. The manual installation below stays as an
alternative. On 23/11/2026, v0.5: secret mode from the Analisar and Comparar versões buttons,
tested end to end (the mode question, the coded copy in a neutral folder, the agent opened there,
the real report built at the end, the same codes across versions), with free mode and the SemIA
buttons unchanged.

History: v0.2 was used end to end on two Windows machines, with GitHub Copilot CLI on one and
Claude Code on the other, and both agents reported the same engine numbers.

| Macro | Does | Data leaves the machine? |
|---|---|---|
| `CronoauditAnalisar` | asks the mode. Free: exports the XML, writes `pedido.md` (the request) and opens the agent in that folder. Secret: exports, runs the engine with `--secret` and opens the agent in the coded folder | free: **yes**, whatever the agent reads goes to its provider. Secret: only the coded copy and what you type |
| `CronoauditComparar` | asks the mode, asks for the other version (.mpp or .xml), exports both, opens the agent with the comparison | same |
| `CronoauditExportarXml` | exports the XML and opens the folder in Explorer | **no**. Nothing is sent, nothing runs |
| `CronoauditSemIA` | exports, runs the engine, opens the HTML report | **no**. Everything runs locally |
| `CronoauditCompararSemIA` | the same for the comparison of two versions | **no** |
| `CronoauditConfigurar` | agent, reports folder, Python, `review.py`, mode, reset | no |

The add-in itself sends nothing; the agent does, under the terms of the user's or the company's
account. Where company policy forbids AI, the two "SemIA" macros produce the same report with no
conversation, and Analisar and Comparar offer that route when no agent is installed.

## Mode: free or secret

Before Analisar or Comparar starts an agent, and before anything is exported, the macro reads
the preference the engine and the skill also read: `%USERPROFILE%\.cronoaudit\config.json`, key
`secret`. The parse is minimal on purpose (it finds that one key); it is not a JSON reader.

| `secret` | What the macro does |
|---|---|
| `ask` (factory default, and whenever the file is missing or unreadable) | a Yes / No / Cancel dialog. Yes: secret mode. No: free mode this time. Cancel: no agent. Yes is the default button, so a stray Enter never sends the schedule to a provider |
| `off` | goes on in free mode without asking |
| `on` | goes on in secret mode without asking (with a note when the agent is not Claude Code) |

Secret mode (experimental), in order: the macro exports the XML to the run folder as in free
mode, and the agent never sees that folder; it runs the engine with `--secret`, which writes the
coded copy to a neutral folder, `%USERPROFILE%\cronoaudit-work\<date-time>\<code>`, with no
schedule name in its path; it opens the agent there with no `pedido.md`, since the request would
carry names (in Claude Code, answer that you trust the folder, or the guard stays off); when you
ask for it, the agent's `finish` builds the real report in the run folder and opens it. The engine is
given the exported XML, never the `.mpp`: exporting through Project from a process the macro is
waiting on would hang both. The guard that keeps the agent inside the folder exists only in
Claude Code; for the other agents the folder carries the same rules as instructions.

This dialog is code, and it runs before any agent exists. In free mode the request it then
writes says the mode was settled, and passes `--free` to the engine; in secret mode the engine
has already run with `--secret` before the agent opens. Either way, neither the skill nor the
engine asks a second time. The two "SemIA" macros also pass `--free`: no agent is involved there, nothing
leaves the machine, and without the flag the engine would ask at its terminal.

v0.3 needs a skill that knows `--free` (the one that ships `cronoaudit_config.py`). With an
older skill installed the macros say so and stop; run the installer again.

The file is written as UTF-8 without a byte-order mark, to a temporary name and then renamed.
Only the value of the key is replaced, so other keys survive.

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
| VS Code (Copilot Chat) | `code "<run folder>"`, prompt on the clipboard | no prompt argument exists; the user opens Copilot Chat in agent mode and pastes |

By default the first one found on PATH is used, in that order; `CronoauditConfigurar` fixes one.
VS Code comes last because it cannot take the prompt on the command line.

`pedido.md` also lists the exact name of every file the engine will write for that run (the
review HTML and JSON, each sidecar, and the cycle files when comparing), so the agent does not
guess a file name.

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
