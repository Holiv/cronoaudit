#!/usr/bin/env python3
"""Secret mode, the run: real analysis into the vault, coded copy into a work folder.
EXPERIMENTAL.

    python3 review.py delivery.xml --secret                  # run by the PERSON, in a terminal
    python3 review.py previous.xml current.xml --secret      # the cycle, same codes on both

What happens, in order:

1. The engine runs exactly as in free mode, on the real file, writing into the
   vault: <cronoaudit folder>/vault/<run-id>/real/. Nothing about the analysis
   changes; that is what makes the coded findings the real findings.
2. Every text of the file the boundary marks (secret_codec.LEGIBILITY) gets a token
   from the project's key. Key, token table, date origin and money factor live in
   <cronoaudit folder>/vault/keys/<project-id>.json and never leave it.
3. Every output is rewritten in code into a fresh work folder, named after nothing
   in the file. The real names, the original's path and the vault's path are not in
   it, nor printed: the leak test in test_checks.py walks the folder to prove it.
4. The work folder carries, for Claude Code, deny rules over the cronoaudit folder
   and a PreToolUse hook (secret_guard.py) that allows only work-folder access and
   the skill's own finishing commands. For other agents it carries instructions,
   and says that they are only instructions.

The person then starts the agent inside the work folder. At the end, the agent (or
the person) runs `secret_decode.py finish`, which decodes the report on this
machine, beside the original and in the vault, and opens it.

Key scope: one key per project. The project is the folder of the current schedule,
or the name given with --project; rev03 and rev04 in the same folder share tokens,
date origin and money factor, so codes compare across versions and across runs.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import sys
import traceback
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import cronoaudit_config as cfg_mod  # noqa: E402
import secret_codec as codec_mod  # noqa: E402

MANIFEST = "cronoaudit-secret.json"
GUARD_NAME = "cronoaudit_guard.py"
GUARD_CONFIG = "cronoaudit_guard.json"
SKILL_DIR = os.path.dirname(HERE)

# The tools the Claude Code hook watches. Anything that can read or write a file.
# PowerShell is on by default in Claude Code on Windows (with Git Bash installed),
# Monitor runs a command, and an MCP server can read files: all are blocked outright.
GUARD_MATCHER = ("Bash|Read|Write|Edit|MultiEdit|NotebookEdit|Grep|Glob|LS|"
                 "PowerShell|Monitor|ReadMcpResourceTool|mcp__.*")
DENIED_TOOLS = ["PowerShell", "Monitor", "ReadMcpResourceTool"]


def vault_dir() -> str:
    return os.path.join(cfg_mod.config_dir(), "vault")


def work_root(args) -> str:
    chosen = getattr(args, "workdir", None) or os.environ.get("CRONOAUDIT_WORK_DIR")
    if chosen:
        return os.path.abspath(os.path.expanduser(chosen))
    return os.path.join(os.path.expanduser("~"), "cronoaudit-work")


def _inside(path: str, folder: str) -> bool:
    path = os.path.normcase(os.path.realpath(path))
    folder = os.path.normcase(os.path.realpath(folder))
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def home_form(path: str) -> str:
    """A path as `~/...` when it is under the home folder, so the files written into
    the work folder do not carry the person's user name."""
    home = os.path.expanduser("~")
    if _inside(path, home):
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(home))
        return "~/" + rel.replace(os.sep, "/")
    return path.replace(os.sep, "/")


def deny_pattern(folder: str) -> str:
    """A Claude Code permission pattern for everything under `folder`.

    `~/x/**` under the home folder, `//abs/x/**` otherwise (a single leading slash
    would be read relative to the settings file). Windows drive paths are written
    the POSIX way Claude Code matches them: C:\\x -> //c/x.
    """
    hf = home_form(folder)
    if hf.startswith("~/"):
        return hf.rstrip("/") + "/**"
    p = os.path.realpath(folder).replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        p = "/" + m.group(1).lower() + "/" + m.group(2)
    return "/" + p.rstrip("/") + "/**"


# ---------------------------------------------------------------------------
# The project's key
# ---------------------------------------------------------------------------
def project_id(args) -> str:
    if getattr(args, "project", None):
        basis = "name:" + args.project.strip()
    else:
        # The folder the person named: an exported .mpp is read from a temporary folder,
        # which must not change the project's codes from one run to the next.
        where = (getattr(args, "origin_files", None) or args.files)[-1]
        basis = "folder:" + os.path.normcase(os.path.realpath(os.path.dirname(os.path.abspath(where))))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _start_of(models) -> date:
    starts = []
    for m in models:
        for key in ("start", "status_date"):
            v = (m.get("project") or {}).get(key)
            if v:
                try:
                    starts.append(datetime.fromisoformat(v).date())
                    break
                except ValueError:
                    pass
    return min(starts) if starts else date.today()


def load_project(pid: str, models, lang: str, currency: str):
    """The project's codec, created on its first secret run and reused after."""
    path = os.path.join(vault_dir(), "keys", pid + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        codec = codec_mod.Codec(bytes.fromhex(d["key"]), date.fromisoformat(d["origin"]), d["k"],
                                d.get("tokens"), d.get("width", codec_mod.WIDTH), lang, currency)
        return codec, path
    rng = secrets.SystemRandom()
    # The origin is a day one to two years before the project starts, so every date
    # of the project is a small positive count and none of them is day zero.
    origin = _start_of(models) - timedelta(days=rng.randint(365, 730))
    # k in (1.5, 9.5): above 1, which the exact decoding of rounded figures needs,
    # and not a round number a reader would guess.
    k = round(rng.uniform(1.5, 9.5), 6)
    codec = codec_mod.Codec(secrets.token_bytes(32), origin, k, {}, codec_mod.WIDTH, lang, currency)
    return codec, path


def save_project(codec, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write_json(path, {"version": 1, "key": codec.key.hex(), "origin": codec.origin.isoformat(),
                       "k": codec.k, "width": codec.width, "tokens": codec.tokens})


def _write_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def _currency(xml_path: str) -> str:
    try:
        with open(xml_path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(65536)
    except OSError:
        return ""
    m = re.search(r"<CurrencySymbol>([^<]{1,8})</CurrencySymbol>", head)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------------------
# Coding the outputs
# ---------------------------------------------------------------------------
def coded_names(files: list) -> dict:
    """Real stem -> neutral stem. Output files are named after the input, and a
    company's file name carries its contract code, so the coded copies are not."""
    stems = [os.path.splitext(os.path.basename(f))[0] for f in files]
    if len(stems) == 1:
        return {stems[0]: "schedule"}
    return {stems[0]: "previous", stems[1]: "current"}


def rename(name: str, files: list) -> str:
    stems = [os.path.splitext(os.path.basename(f))[0] for f in files]
    if len(stems) == 2:
        cyc = f"{stems[0]}--to--{stems[1]}-cycle"
        if name.startswith(cyc):
            return "previous--to--current-cycle" + name[len(cyc):]
        if name.startswith(stems[1] + "-review"):
            return "current" + name[len(stems[1]):]
        if name.startswith(stems[0] + "-review"):
            return "previous" + name[len(stems[0]):]
    elif name.startswith(stems[0] + "-review"):
        return "schedule" + name[len(stems[0]):]
    raise ValueError("an output whose name is not one the engine writes")


def code_payload(codec, payload: dict, sources: dict | None = None) -> dict:
    """The report payload, coded. The real payload is not changed. `sources` adds what
    a prose site needs that the payload does not carry (the cycle sidecar)."""
    real = json.loads(json.dumps(payload))
    work = json.loads(json.dumps(payload))
    codec_mod.mark_prose_money(work.get("readings"), {**(sources or {}), **real},
                               real.get("lang", "en"), codec)
    if sources:
        work = codec_mod.mark_prose_money_everywhere(work, {**sources, **real},
                                                     real.get("lang", "en"), codec)
    for path in codec_mod.LEGIBILITY["withheld"]:
        codec_mod.withhold(work, path)
    return codec.encode_obj(work)


def code_sidecar(codec, name: str, obj, review_payload: dict | None, cycle_data: dict | None = None):
    work = json.loads(json.dumps(obj))
    if name.endswith("-review-readings.json") and review_payload is not None:
        codec_mod.mark_prose_money(work.get("readings"), review_payload,
                                   review_payload.get("lang", "en"), codec)
    if name.endswith("-cycle-readings.json") and cycle_data is not None:
        codec_mod.mark_prose_money(work.get("readings"), cycle_data,
                                   work.get("lang") or "en", codec)
    if name.endswith("-review-forecast.json"):
        # The forecast sidecar is the payload's `forecast`, so the same series goes.
        for path in codec_mod.LEGIBILITY["withheld"]:
            if path[0] == "forecast":
                codec_mod.withhold(work, path[1:])
    return codec.encode_obj(work)


def console_text(captured: str) -> str:
    """The engine's console summary without the lines that name output paths."""
    keep = [ln for ln in captured.splitlines()
            if not ln.startswith("  report   ") and not ln.startswith("  data     ")]
    return "\n".join(keep).strip("\n")


# ---------------------------------------------------------------------------
# The work folder's protection
# ---------------------------------------------------------------------------
def python_name() -> str:
    """The interpreter name to write in commands: on Windows `python3` is often the
    Store stub that installs nothing and runs nothing; `python` is what the
    installer puts on PATH."""
    return "python" if os.name == "nt" else "python3"


def agent_notes(script_dir: str, lang: str) -> str:
    s = script_dir
    py = python_name()
    return f"""# cronoaudit: SECRET-mode work folder (experimental)

Every file here is a CODED copy of a schedule review. Names are tokens (`T·3fa91c`),
money is multiplied by a secret factor, dates are day counts from a secret origin
(`D+0412`, `d+0412` is the same day in display form, `M+0013` a month, `Y+0001` a year).
Durations, percentages, counts, ratios, row IDs and WBS codes are real.

- Use the cronoaudit skill in SECRET mode. Read only the files in this folder.
- Never ask for, look for or open the original schedule, and never run review.py.
- Quote tokens and codes exactly as written. Write coded money with the mark,
  in the report's notation: `¤1.234.567` (a figure without the mark is not decoded).
- Never run `secret_decode.py text`: it prints real names, and only the person runs it.
- To finish (write commands with full paths, no variables; for a cycle the report is
  current-review.html):
    {py} {s}/inject_narrative.py schedule-review.html synthesis.txt --who "<agent>, via the skill"
    {py} {s}/secret_decode.py finish
  `finish` decodes on this machine and prints nothing from the schedule.

For Claude Code this folder carries deny rules and a hook (`.claude/`) that block
reading outside it. For any other agent these lines are an instruction, not an
enforcement: nothing technical stops it from opening other files.
"""


def write_guard(workdir: str) -> None:
    hooks = os.path.join(workdir, ".claude", "hooks")
    os.makedirs(hooks, exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "secret_guard.py"), os.path.join(hooks, GUARD_NAME))
    _write_json(os.path.join(hooks, GUARD_CONFIG), {
        "experimental": True,
        # Where the skill's scripts are, so its finishing commands are allowed. The
        # work folder is the hook's own grandparent and is not written anywhere.
        "skill_dir": home_form(SKILL_DIR),
    })
    python = sys.executable.replace("\\", "/")
    deny_dir = deny_pattern(cfg_mod.config_dir())
    _write_json(os.path.join(workdir, ".claude", "settings.json"), {
        "permissions": {
            # Edit also covers Write and NotebookEdit; Read also covers Grep and Glob,
            # on a best-effort basis per the Claude Code documentation. Neither covers
            # Bash: that is the hook's job.
            # The tools that run commands or reach files outside the hook's rules
            # are also denied by Claude Code itself, so they stay closed even if
            # the hook cannot start.
            "deny": [f"Read({deny_dir})", f"Edit({deny_dir})"] + DENIED_TOOLS,
        },
        "env": {"CLAUDE_CODE_USE_POWERSHELL_TOOL": "0"},
        "hooks": {"PreToolUse": [{"matcher": GUARD_MATCHER, "hooks": [{
            "type": "command",
            "command": f'"{python}" "${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{GUARD_NAME}"',
            "timeout": 30,
            # A hook that cannot start (wrong interpreter, PowerShell reading the
            # quoted path as a string) would otherwise let every call through.
            # Honoured from Claude Code 2.1.295; older versions ignore it.
            "onFailure": "block"}]}]},
    })


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------
def run(args) -> int:
    import i18n
    import inject_narrative
    import report_html
    import review

    lang_ui = args.lang or cfg_mod.system_lang()
    txt = i18n.modes_text(lang_ui)
    review.say(txt["secret_running"])

    files = [os.path.abspath(f) for f in args.files]
    if len(files) > 2:
        raise SystemExit("Pass one file to review, or two to compare. More than two is ambiguous.")
    for n, f in enumerate(files, 1):
        if not os.path.exists(f):
            # The person's terminal, but stdout and stderr stay free of the path anyway.
            raise SystemExit(f"cronoaudit: schedule {n} not found")

    root = work_root(args)
    run_id = secrets.token_hex(5)
    workdir = os.path.join(root, run_id)
    vault_run = os.path.join(vault_dir(), run_id)
    if _inside(root, cfg_mod.config_dir()) or any(_inside(os.path.dirname(f), workdir)
                                                  or _inside(workdir, os.path.dirname(f))
                                                  for f in files):
        review.say(txt["secret_workdir_bad"])
        return 1

    real_dir = os.path.join(vault_run, "real")
    os.makedirs(real_dir, exist_ok=True)
    out, err = io.StringIO(), io.StringIO()
    try:
        # 1. The real analysis, unchanged, into the vault. Its console output names
        # real activities and real paths, so it is captured, not shown.
        ns = type(args)(**vars(args))
        ns.files = files
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            models = review.analyse(ns, real_dir)

        # 2. The project's codes.
        names = os.listdir(real_dir)
        review_html = next(n for n in names if n.endswith("-review.html"))
        with open(os.path.join(real_dir, review_html), encoding="utf-8") as fh:
            review_payload = inject_narrative.extract(fh.read())
        lang = review_payload.get("lang", "en")
        codec, key_path = load_project(project_id(args), models, lang, _currency(files[-1]))
        import profile as prof_mod
        pairs = []
        for f, m in zip(files, models):
            pairs += codec_mod.collect_file(f) + codec_mod.collect_xml(f) + codec_mod.collect_model(m)
        pairs += codec_mod.collect_profile(prof_mod.load(args.profile))
        codec.add(pairs)

        # 3. Refuse rather than code what could not be decoded exactly.
        real_objs = {}
        for n in names:
            with open(os.path.join(real_dir, n), encoding="utf-8") as fh:
                raw = fh.read()
            real_objs[n] = inject_narrative.extract(raw) if n.endswith(".html") else json.loads(raw)
        clashes = sum(codec_mod.find_code_like(o) for o in real_objs.values()) \
            + (1 if codec_mod.CODE_LIKE.search(out.getvalue()) else 0)
        if clashes:
            review.say(txt["secret_refused_codes"].format(n=clashes))
            shutil.rmtree(vault_run, ignore_errors=True)
            return 1
        save_project(codec, key_path)

        # 4. The coded copy.
        os.makedirs(workdir)
        template = args.template or (prof_mod.load(args.profile).get("template"))
        # The coded copy is always written with the shipped template. A customised
        # one is the organisation's own branding and can carry its name; it is used
        # again on the way back, by `finish`, on this machine.
        shipped = os.path.join(SKILL_DIR, "templates", "report.html")
        coded_files = []
        cycle_data = next((real_objs[n] for n in names if n.endswith("-cycle.json")), None)
        for n in sorted(names):
            target = os.path.join(workdir, rename(n, files))
            if n.endswith(".html"):
                src = cycle_data if n.endswith("-cycle.html") else None
                report_html.write(code_payload(codec, real_objs[n], src), target, shipped)
            else:
                _write_json(target, code_sidecar(codec, n, real_objs[n], review_payload, cycle_data))
            coded_files.append(os.path.basename(target))
        script_dir = home_form(HERE)
        _write_json(os.path.join(workdir, MANIFEST), {
            "cronoaudit": "secret mode", "experimental": True, "run": run_id,
            "lang": lang, "files": coded_files,
            "codes": {"token": "T·3fa91c (letter = kind: " + ", ".join(
                f"{k} {v}" for k, v in codec_mod.CATEGORIES.items()) + ")",
                "D+0412": "a day, counted from a secret origin; d+0412 is the same day in display form",
                "M+0013": "a month from the origin's month", "Y+0001": "a year from the origin's year",
                "money": "multiplied by a secret factor; write it as ¤1.234.567 in the report's notation"},
            "money_keys": sorted(codec_mod.LEGIBILITY["money_keys"]),
            "legible": codec_mod.LEGIBILITY["legible"],
            "withheld": [".".join(p) for p in codec_mod.LEGIBILITY["withheld"]],
            "finish": f"{python_name()} {script_dir}/secret_decode.py finish",
        })
        notes = agent_notes(script_dir, lang)
        for doc in ("CLAUDE.md", "AGENTS.md"):
            with open(os.path.join(workdir, doc), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(notes)
        write_guard(workdir)

        # 5. What decoding needs, in the vault (never in the work folder).
        _write_json(os.path.join(vault_run, "back.json"), codec.back_table())
        _write_json(os.path.join(vault_run, "run.json"), {
            "run": run_id, "project": project_id(args), "workdir": workdir,
            # Where the person's files are: `finish` writes the decoded report beside them.
            "files": [os.path.abspath(f) for f in (getattr(args, "origin_files", None) or files)],
            "template": template, "lang": lang,
            "created": datetime.now().isoformat(timespec="seconds"),
            "html": {rename(n, files): n for n in names if n.endswith(".html")},
        })
        with open(os.path.join(vault_run, "engine-console.txt"), "w", encoding="utf-8") as fh:
            fh.write(out.getvalue() + "\n" + err.getvalue())
    except Exception as exc:  # the details may name the schedule: they stay in the vault
        os.makedirs(vault_run, exist_ok=True)
        with open(os.path.join(vault_run, "error.log"), "w", encoding="utf-8") as fh:
            fh.write(traceback.format_exc() + "\n" + err.getvalue())
        shutil.rmtree(workdir, ignore_errors=True)
        review.say(txt["secret_failed"].format(error=type(exc).__name__))
        return 1

    # 6. What the person sees: coded, plus the work folder. Never the vault, never the original.
    if not args.quiet:
        shown = codec.encode_text(console_text(out.getvalue()))
        if shown:
            print(shown)
            print()
    print(txt["secret_ready"].format(workdir=workdir))
    return 0
