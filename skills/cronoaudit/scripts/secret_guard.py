#!/usr/bin/env python3
"""Secret mode, the Claude Code guard: a PreToolUse hook.

Copied by secret_mode.py into <work folder>/.claude/hooks/ and registered in
<work folder>/.claude/settings.json. Claude Code sends each tool call as JSON on
stdin; exit 0 lets it through, exit 2 blocks it and shows stderr to the agent.

It ALLOWS what a secret session needs and blocks everything else, instead of
blocking known paths: a path can be built at run time, globbed, or reached through
`cd ..`, and a list of forbidden places would also have to name the original's
folder, which carries the company's name. So nothing here names the vault or the
original. Allowed:

  Read, Grep, Glob, LS   inside the work folder or the skill's own folder
  Write, Edit, ...       inside the work folder, never its .claude/ folder
  Bash                   only these, each argument resolving inside the work folder:
                           - the skill's inject_narrative.py and `secret_decode.py finish`
                             run by a Python interpreter
                           - plain reading commands (ls, cat, head, tail, wc, grep,
                             sort, uniq, cut, jq, echo, pwd, cd, diff), piped or chained
                         no variables, no command substitution, no other interpreter
  as they are            tools that touch no file and send nothing anywhere: Skill,
                         ToolSearch, AskUserQuestion, the task list, plan mode, and Agent
                         (a subagent's own calls come through this hook too)
  nothing else           every other tool is blocked, known or not: PowerShell (on by
                         default on Windows), Monitor, MCP and connector tools, Artifact,
                         SendUserFile, SendMessage (another session is not guarded),
                         Workflow, and whatever a later version of the agent adds. Each
                         of these can read a file or carry text out by another road.

What this is: a tripwire against an agent wandering out of the folder by habit or
by an instruction it misread. What it is not: a sandbox against an agent set on
escaping; an allowed program could still be asked to do something unforeseen.
Anything this script cannot parse is blocked, and so is any error inside it: a
hook that crashes would otherwise let the call through.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Tools that touch no file and send nothing out: let through as they are. Every
# tool not named here or checked below is blocked, so a tool added in a later
# version of the agent starts closed.
PASS_TOOLS = {"Skill", "ToolSearch", "AskUserQuestion", "TodoWrite", "TaskCreate", "TaskGet",
              "TaskList", "TaskUpdate", "EnterPlanMode", "ExitPlanMode", "Agent", "Task"}

READ_COMMANDS = {"ls", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "sort", "uniq",
                 "cut", "jq", "echo", "printf", "pwd", "cd", "diff", "true"}
SKILL_SCRIPTS = {"inject_narrative.py", "secret_decode.py"}
PYTHON = re.compile(r"^(?:python(?:\d+(?:\.\d+)?)?|py)(?:\.exe)?$", re.I)
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob", "LS"}


class Blocked(Exception):
    pass


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _inside(path: str, folder: str) -> bool:
    p, f = _norm(path), _norm(folder)
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def _git_bash_path(p: str) -> str:
    # Git Bash on Windows writes C:\x as /c/x.
    if os.name == "nt":
        m = re.match(r"^/([A-Za-z])(/.*)?$", p)
        if m:
            return m.group(1) + ":" + (m.group(2) or "/")
    return p


class Guard:
    def __init__(self, workdir: str, skill_dir: str):
        self.work = os.path.realpath(workdir)
        self.skill = os.path.realpath(os.path.expanduser(skill_dir)) if skill_dir else None
        self.claude_dir = os.path.join(self.work, ".claude")

    # ---- paths
    def resolve(self, raw: str, cwd: str) -> str:
        if "$" in raw or "`" in raw:
            raise Blocked("variables and command substitution are not allowed in a secret session")
        p = _git_bash_path(os.path.expanduser(raw))
        if not os.path.isabs(p):
            p = os.path.join(cwd, p)
        return os.path.realpath(p)

    def readable(self, raw: str, cwd: str) -> None:
        p = self.resolve(raw, cwd)
        if _inside(p, self.work) or self._skill_public(p):
            return
        raise Blocked("outside the secret work folder")

    def _skill_public(self, p: str) -> bool:
        """The skill's own public files: its text, references, scripts and shipped
        template. Not the rest of its folder, where an organisation keeps a
        customised template or a profile that can carry its name."""
        if not self.skill or not _inside(p, self.skill):
            return False
        if _norm(p) == _norm(self.skill):
            return True
        allowed = [os.path.join(self.skill, "SKILL.md"), os.path.join(self.skill, "references"),
                   os.path.join(self.skill, "scripts"), os.path.join(self.skill, "templates", "report.html")]
        return any(_inside(p, a) for a in allowed)

    def writable(self, raw: str, cwd: str) -> None:
        p = self.resolve(raw, cwd)
        if not _inside(p, self.work) or _inside(p, self.claude_dir):
            raise Blocked("writing is allowed only inside the work folder, outside .claude/")

    @staticmethod
    def _glob_root(pattern: str) -> str:
        cut = re.split(r"[*?\[{]", pattern, 1)[0]
        return cut or "."

    # ---- tools
    def check(self, call: dict) -> None:
        tool = call.get("tool_name") or ""
        inp = call.get("tool_input") or {}
        cwd = call.get("cwd") or self.work
        if not _inside(cwd, self.work):
            raise Blocked("the session is no longer inside the secret work folder")
        if tool in WRITE_TOOLS:
            self.writable(inp.get("file_path") or inp.get("notebook_path") or "", cwd)
        elif tool == "Read":
            self.readable(inp.get("file_path") or "", cwd)
        elif tool in ("Grep", "LS"):
            self.readable(inp.get("path") or cwd, cwd)
        elif tool == "Glob":
            self.readable(inp.get("path") or cwd, cwd)
            pat = inp.get("pattern") or ""
            self.readable(os.path.join(inp.get("path") or cwd, self._glob_root(pat)), cwd)
        elif tool == "Bash":
            self.bash(inp.get("command") or "", cwd)
        elif tool not in PASS_TOOLS:
            raise Blocked(f"{tool or 'this tool'} is not allowed in a secret session "
                          "(read and write the files in this folder; Bash for the finishing commands)")

    def bash(self, command: str, cwd: str) -> None:
        if re.search(r"[`$]|<\(|>\(|\n|\r", command):
            raise Blocked("variables, substitutions and multi-line commands are not allowed in a secret session")
        # `2>&1` is a redirection, not a background `&`: taken out before splitting.
        command = re.sub(r"(?<=\s)\d*>&\d+", " ", command)
        segments = re.split(r"\|\||&&|[|;&]", command)
        for seg in segments:
            if seg.strip():
                cwd = self.segment(seg, cwd)

    def segment(self, seg: str, cwd: str) -> str:
        try:
            words = shlex.split(seg, posix=True)
        except ValueError:
            raise Blocked("a command this guard cannot read")
        args, i = [], 0
        while i < len(words):
            w = words[i]
            m = re.match(r"^(\d*)(>>?|<)(&\d+)?(.*)$", w)
            if m and (m.group(2) or "") and not m.group(3):
                target = m.group(4) or (words[i + 1] if i + 1 < len(words) else "")
                if not m.group(4):
                    i += 1
                if target not in ("/dev/null", "nul", "NUL"):
                    (self.readable if m.group(2) == "<" else self.writable)(target, cwd)
                i += 1
                continue
            if m and m.group(3):        # 2>&1
                i += 1
                continue
            args.append(w)
            i += 1
        if not args:
            return cwd
        if "=" in args[0] and not args[0].startswith(("-", "/", ".")):
            raise Blocked("environment assignments are not allowed in a secret session")
        cmd = os.path.basename(_git_bash_path(args[0]))
        if PYTHON.match(cmd):
            self.python(args[1:], cwd)
            return cwd
        if cmd not in READ_COMMANDS:
            raise Blocked(f"`{cmd}` is not among the commands a secret session allows")
        for a in args[1:]:
            self._arg(a, cwd)
        if cmd == "cd":
            target = next((a for a in args[1:] if not a.startswith("-")), "~")
            self.readable(target, cwd)
            new = self.resolve(target, cwd)
            if not _inside(new, self.work):
                raise Blocked("cd outside the secret work folder")
            return new
        return cwd

    def _arg(self, a: str, cwd: str) -> None:
        """Any argument that could name a place is checked as a path; a relative one
        without `..` stays inside the current folder, which is inside the work folder."""
        value = a.split("=", 1)[1] if a.startswith("-") and "=" in a else a
        if a.startswith("-") and "=" not in a:
            return
        if (value.startswith(("/", "\\", "~", ".")) or re.match(r"^[A-Za-z]:", value)
                or ".." in value.replace("\\", "/").split("/")
                or os.path.lexists(os.path.join(cwd, value))):   # a symlink in the folder is followed
            self.readable(self._glob_root(value) if re.search(r"[*?\[]", value) else value, cwd)

    def python(self, args: list, cwd: str) -> None:
        rest = [a for a in args if a not in ("-I", "-S", "-B", "-u", "-E", "-s")]
        if not rest or rest[0].startswith("-"):
            raise Blocked("Python may run only the skill's finishing scripts in a secret session")
        script = self.resolve(rest[0], cwd)
        if not (self.skill and _inside(script, os.path.join(self.skill, "scripts"))
                and os.path.basename(script) in SKILL_SCRIPTS):
            raise Blocked("Python may run only inject_narrative.py and secret_decode.py finish")
        if os.path.basename(script) == "secret_decode.py":
            positional = [a for a in rest[1:] if not a.startswith("-")]
            if not positional or positional[0] != "finish":
                raise Blocked("only `secret_decode.py finish` may run here; `text` is the person's own command")
        for a in rest[1:]:
            self._arg(a, cwd)


def load_guard() -> Guard:
    workdir = os.path.dirname(os.path.dirname(HERE))   # <work>/.claude/hooks/this.py
    with open(os.path.join(HERE, "cronoaudit_guard.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    return Guard(workdir, cfg.get("skill_dir") or "")


def decide(guard: Guard, call: dict):
    """(allowed, reason). Pure, for the tests."""
    try:
        guard.check(call)
        return True, ""
    except Blocked as exc:
        return False, str(exc)


def from_claude_code(call) -> bool:
    """Whether Claude Code itself started this hook.

    Another agent also reads this folder's .claude/settings.json and runs the hook:
    GitHub Copilot CLI does, and it sends Claude Code's own payload shape, so the payload
    proves nothing (measured). What Claude Code gives its hooks and other agents do not
    is its own environment: CLAUDECODE and CLAUDE_CODE_SESSION_ID, present in the hook
    of a Claude Code started from a clean environment (measured). The guard knows only
    Claude Code's tools, so anywhere else it steps aside and the folder's written rules
    are what apply, as the documentation says for every agent but Claude Code."""
    return bool(os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_SESSION_ID"))


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    try:
        call = json.loads(sys.stdin.read() or "{}")
        if not isinstance(call, dict):
            raise ValueError("payload is not an object")
        if not from_claude_code(call):
            return 0
        ok, reason = decide(load_guard(), call)
    except Exception as exc:   # fail closed
        ok, reason = False, f"the secret-mode guard could not check this call ({type(exc).__name__})"
    if ok:
        return 0
    sys.stderr.write("cronoaudit secret mode: blocked, " + reason + ". Work only with the coded "
                     "files in this folder; the person can switch to free mode if needed.\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
