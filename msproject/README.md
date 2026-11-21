# cronoaudit inside MS Project

Status: **v0.1, not yet run on a real machine.** Run the feasibility probe first.

A VBA module for MS Project (Windows) that removes the manual steps around the tool:

| Macro | Does | Data leaves the machine? |
|---|---|---|
| `CronoauditAuditar` | exports the open schedule to XML, runs `review.py`, opens the report | no |
| `CronoauditComparar` | asks for the other version (.mpp or .xml), exports it read-only, runs the cycle comparison | no |
| `CronoauditConversar` | opens the agent found on PATH (Claude Code, Copilot, Codex, Gemini, VS Code) in the results folder | yes, whatever the agent reads |
| `CronoauditConfigurar` | Python command, `review.py` path, reports folder | |

The command-line route stays the primary, cross-platform one. Reports go to
`%LOCALAPPDATA%\cronoaudit\relatorios`, outside any synced folder, because they carry project data.

- `CronoauditTeste.bas`: the feasibility probe (XML export by macro, which document is active
  afterwards, whether a macro may start a process, whether Python 3.9+ is reachable).
- `Cronoaudit.bas`: the add-in module, imported into `Global.MPT`. It never replaces the Global.
- `LEIA-ME.md`: install, test and troubleshooting guide (Portuguese).

The `.bas` files are stored as cp1252 with CRLF line endings, because the VBA editor imports ANSI.
