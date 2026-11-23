#!/usr/bin/env python3
"""One command. Point it at a schedule export and get a review plus an HTML report.

    python3 review.py delivery.xml
    python3 review.py previous.xml current.xml
    python3 review.py delivery.mpp                  # if the optional reader is installed

One file  -> critical review of that delivery.
Two files -> the earlier one is the previous snapshot; you get the cycle comparison
             AND a review of the current file, because comparing two files neither
             of which holds together is comparing two wrong answers.

Everything is written next to the input unless you pass --outdir. Nothing is sent
anywhere, nothing is fetched, and the HTML has no external references, so it opens
on a machine with no network and looks the same there.

Modes. The engine sends nothing either way; the mode is about what an AGENT reads.

    python3 review.py delivery.xml --free       # free mode, said explicitly
    python3 review.py delivery.xml --secret     # secret mode (experimental): a coded work folder
    python3 review.py --secret on|off|ask       # store the preference and exit
    python3 review.py --config                  # print the stored preference

With neither flag the stored preference decides (~/.cronoaudit/config.json): "on" is
--secret, "off" is --free, and "ask" asks at a terminal or, when nobody can answer,
says on stderr that the run is in free mode and goes on. The mode is settled before
any schedule is opened.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compare_snapshots  # noqa: E402
import cronoaudit_config as cfg_mod  # noqa: E402
import parse_mspdi  # noqa: E402
import phasing as phasing_mod  # noqa: E402
import resources as resources_mod  # noqa: E402
import network_quality as quality_mod  # noqa: E402
import forecast as forecast_mod  # noqa: E402
import forensics as forensics_mod  # noqa: E402
import profile as prof_mod  # noqa: E402
import report_data  # noqa: E402
import report_html  # noqa: E402
import run_checks  # noqa: E402

MPP_HELP = """
This is a .mpp file, which is a proprietary binary that nothing can read without
Project itself or a dedicated library.

The dependency-free route, and the one to prefer -- it takes about fifteen seconds
and no install:

    In MS Project:  File > Save As  ->  choose "XML Format (*.xml)"
    Then:           python3 review.py <that file>.xml

The XML is Project's own documented format. It carries the tasks, the links, the
eleven baseline slots, the calendars and the custom fields, so nothing needed here
is lost in the export.

If you would rather read .mpp directly and have a Java runtime available:

    pip install mpxj

and run this command again. Primavera P6 XER and P6 XML also come in through that
library -- but be aware that the checks in this skill were measured against MS
Project files, not P6, so treat a P6 result as unverified.
"""


def load(path: str) -> dict:
    """Parse a schedule export into the canonical model."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xml":
        return parse_mspdi.parse(path)
    if ext in (".mpp", ".xer", ".mpx"):
        model = try_mpxj(path)
        if model is None:
            raise SystemExit(MPP_HELP.strip())
        # The model was parsed from a temporary conversion; the name a person
        # recognises is the file they passed.
        model["source"] = os.path.basename(path)
        return model
    raise SystemExit(
        f"{path}: unrecognised extension {ext!r}. Expected .xml from "
        "File > Save As > XML Format."
    )


def try_mpxj(path: str):
    """Optional path: convert via the mpxj library if the user happens to have it.

    Kept strictly optional. The skill must work with nothing installed beyond
    Python, because a tool that needs a Java runtime before it answers anything
    does not get adopted by the person who received a file this morning.
    """
    try:
        import mpxj  # noqa: F401
        import jpype
        from mpxj import ProjectWriterUtility  # noqa: F401
    except Exception:
        return None
    try:
        import tempfile

        import mpxj
        jpype.startJVM()
        from net.sf.mpxj.reader import UniversalProjectReader
        from net.sf.mpxj.writer import UniversalProjectWriter
        from net.sf.mpxj.writer import FileFormat

        project = UniversalProjectReader().read(path)
        tmp = os.path.join(tempfile.mkdtemp(), "converted.xml")
        UniversalProjectWriter(FileFormat.MSPDI).write(project, tmp)
        return parse_mspdi.parse(tmp)
    except Exception as exc:  # pragma: no cover - depends on optional install
        print(f"the optional reader failed ({exc}); falling back", file=sys.stderr)
        return None


def stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def do_review(model, path, outdir, threshold, tolerance, quiet,
              theme=None, grouping="wbs", template=None, lang=None,
              previous=None, cycle=None, profile=None) -> dict:
    profile = profile or prof_mod.load(None)
    # A profile may force the baseline slot or the earned-value method. Both are
    # recorded as forced, so the report says the choice was the organisation's,
    # not the file's.
    if profile.get("baseline_slot") is not None:
        model["prevailing_baseline"] = {**(model.get("prevailing_baseline") or {}),
                                        "slot": str(profile["baseline_slot"]),
                                        "basis": "forced by the organisation profile"}
    if profile.get("ev_method"):
        model["project"]["ev_method_forced"] = profile["ev_method"]
    res = run_checks.run(model, threshold, tolerance)
    # The S-curve reads the XML a second time, streaming, because the phased
    # blocks are too many to keep in the model. XML only: the optional binary
    # reader converts to a temporary XML, which is fine, but a file that came in
    # some other way has no phasing to read.
    curve = None
    prod = None
    quality = None
    # The path, not the display name: `source` is a file name only, by design.
    src = model.get("source_path")
    if src and src.lower().endswith(".xml") and os.path.exists(src):
        grp = report_data.resolve_grouping(model, grouping)
        curve = phasing_mod.build(src, grp.get("field_id"))
        prod = resources_mod.build(src, model, profile=profile)
    quality = quality_mod.build(model, src if (src and src.lower().endswith(".xml")
                                              and os.path.exists(src)) else None)
    fc = None
    if curve is not None:
        grp = report_data.resolve_grouping(model, grouping)
        fc = forecast_mod.build(model, curve, prod, grp.get("field_id"), profile=profile)
    grp = report_data.resolve_grouping(model, grouping)
    fx = forensics_mod.build(model, res, previous, cycle, grp.get("field_id"))
    base = os.path.join(outdir, f"{stem(path)}-review")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    import i18n
    effective_lang = lang or i18n.detect(model)["lang"]
    payload = report_data.build_review(model, res, theme=theme, grouping=grouping,
                                       lang=effective_lang, phasing=curve, profile=profile,
                                       productivity=prod, quality=quality, forecast=fc,
                                       forensics=fx)
    with open(base + "-forensics.json", "w", encoding="utf-8") as fh:
        json.dump(fx, fh, indent=2, ensure_ascii=False)
    if fc is not None:
        with open(base + "-forecast.json", "w", encoding="utf-8") as fh:
            json.dump(fc, fh, indent=2, ensure_ascii=False)
    with open(base + "-quality.json", "w", encoding="utf-8") as fh:
        # Labelled so a reader of the sidecar alone knows what Q6 or Q14 is.
        json.dump(report_data.localize_quality(quality, effective_lang), fh, indent=2,
                  ensure_ascii=False)
    with open(base + "-readings.json", "w", encoding="utf-8") as fh:
        # The rule-built sentences the report shows, so an assistant can quote them
        # instead of composing its own.
        # `inputs` says what each reading needed and whether the file had it.
        json.dump({"lang": effective_lang, "language": payload.get("language"),
                   "inputs": (payload.get("meta") or {}).get("inputs"),
                   "baseline": (payload.get("meta") or {}).get("baseline_label"),
                   "readings": payload.get("readings")}, fh, indent=2, ensure_ascii=False)
    if curve is not None:
        with open(base + "-scurve.json", "w", encoding="utf-8") as fh:
            json.dump(curve, fh, indent=2, ensure_ascii=False)
    if prod is not None:
        with open(base + "-productivity.json", "w", encoding="utf-8") as fh:
            json.dump(prod, fh, indent=2, ensure_ascii=False)
    report_html.write(payload, base + ".html", template)
    # Handed to the cycle report, which opens C1 with the same table. Not written.
    res["_deadlines"] = payload.get("deadlines")
    if not quiet:
        print(run_checks.report(res, effective_lang))
        print()
    print(f"  report   {base}.html")
    print(f"  data     {base}.json")
    return res


# The exit code of a run that stopped because secret mode was asked for. Distinct
# from 1 (an error, or a cancelled question) and 2 (bad arguments), so a caller can
# tell "refused on purpose" from "failed".
EXIT_SECRET = 3

SECRET_FLAGS = ("--secret", "--secreto")


def normalise_mode_args(argv: list) -> list:
    """Make `--secret` unambiguous before argparse sees it.

    `--secret` alone runs in secret mode; `--secret on|off|ask` stores a preference.
    An optional value would swallow the schedule in `--secret delivery.xml`, so the
    flag is rewritten here to always carry one: the word that follows when it is
    on, off or ask, and "run" otherwise.
    """
    out, i = [], 0
    while i < len(argv):
        tok = argv[i]
        if tok in SECRET_FLAGS:
            nxt = argv[i + 1].lower() if i + 1 < len(argv) else ""
            if nxt in cfg_mod.VALUES:
                out.append("--secret=" + nxt)
                i += 2
                continue
            out.append("--secret=run")
        elif tok.split("=", 1)[0] in SECRET_FLAGS and "=" in tok:
            out.append("--secret=" + tok.split("=", 1)[1].lower())
        else:
            out.append(tok)
        i += 1
    return out


def say(text: str, stream=None) -> None:
    """Print without ever failing on a console that cannot show an accent."""
    stream = stream or sys.stderr
    try:
        print(text, file=stream)
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "ascii"
        print(text.encode(enc, "replace").decode(enc), file=stream)
    stream.flush()


def describe_config(state: dict, txt: dict) -> str:
    """The stored preference, first line stable for a program to read: `secret: ask`."""
    lines = [f"secret: {state['secret']}", "  " + txt["state_" + state["secret"]],
             "  " + txt["config_file"].format(path=state["path"])]
    if state["status"] == "missing":
        lines.append("  " + txt["config_missing"])
    elif state["status"] == "corrupt":
        lines.append("  " + txt["config_corrupt"].format(detail=state["detail"]))
    elif state["status"] == "invalid":
        lines.append("  " + txt["config_invalid"].format(detail=state["detail"]))
    lines.append("  " + txt["config_how"])
    return "\n".join(lines)


def agent_environment() -> str | None:
    """The name of the variable that says an agent started this process, if one does.

    Secret mode protects only if the agent never holds the original, so the coded
    run must be started by the person (or by the MS Project add-in), not by the
    agent. Claude Code documents CLAUDE_CODE_CHILD_SESSION for the processes its
    tools start and CLAUDECODE for those and for IDE terminals. Other agents
    document no such variable, so for them this check does nothing; SKILL.md says so.
    """
    for name in ("CLAUDE_CODE_CHILD_SESSION", "CLAUDECODE"):
        if os.environ.get(name):
            return name
    return None


def stop_for_secret(origin_key: str, state: dict, langs: list, reason: str = "secret_stop") -> None:
    """Secret mode was asked for and cannot run here: stop, having read nothing.

    Never a fallback to free mode. The person who asked for secret and got a free
    run would have sent the schedule to a provider believing they had not.
    """
    import i18n
    for n, lang in enumerate(langs):
        txt = i18n.modes_text(lang)
        if n:
            say("")
        say(txt[reason].format(origin=txt[origin_key].format(path=state["path"]),
                               variable=agent_environment() or ""))
    raise SystemExit(EXIT_SECRET)


def ask_mode(state: dict, txt: dict, langs: list) -> str:
    """The question, at a terminal. Returns "free" or "secret"; exits otherwise."""
    for _attempt in range(3):
        say(txt["question"])
        sys.stderr.write("> ")
        sys.stderr.flush()
        line = sys.stdin.readline()
        if not line:  # end of input: nobody is there after all
            break
        answer = line.strip().lower()
        if answer in ("s", "sim", "y", "yes", "l", "livre", "free"):
            return "free"
        if answer in ("secreto", "secret"):
            return "secret"
        if answer in ("nunca", "never"):
            try:
                path = cfg_mod.set_secret("off")
                say(txt["never_saved"].format(path=path))
            except OSError as exc:
                say(txt["never_failed"].format(path=state["path"], error=exc))
            return "free"
        if answer in ("n", "nao", "não", "no", "c", "cancelar", "cancel"):
            say(txt["cancelled"])
            raise SystemExit(1)
        say(txt["question_retry"])
    say(txt["no_answer"])
    raise SystemExit(1)


def settle_mode(args, lang_forced) -> str:
    """Decide the mode of this run: "free" or "secret". Called before any schedule
    is opened. Exits when the run must not go on.
    """
    import i18n
    lang = lang_forced or cfg_mod.system_lang()
    txt = i18n.modes_text(lang)
    # The stop message matters most, and the language is a guess unless --lang was
    # given: say it in the guessed language and then in the other one.
    langs = [lang] if lang_forced else [lang, "en" if lang == "pt" else "pt"]
    state = cfg_mod.load()
    try:
        interactive = sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError):
        interactive = False
    mode = cfg_mod.decide(args.secret == "run", args.free, state["secret"], interactive)
    origin = "origin_flag" if args.secret == "run" else "origin_pref"
    if mode == "ask":
        if state["status"] in ("corrupt", "invalid"):
            say("cronoaudit: " + txt["config_" + state["status"]].format(detail=state["detail"]))
        mode = ask_mode(state, txt, langs)
        origin = "origin_answer"
    elif mode == "notice":
        if state["status"] in ("corrupt", "invalid"):
            say("cronoaudit: " + txt["config_" + state["status"]].format(detail=state["detail"]))
        say(txt["notice"])
        mode = "free"
    if mode == "secret" and agent_environment():
        # Started by an agent: the agent already holds the path of the original, so
        # coding the output would protect nothing. Stop; the person runs it.
        stop_for_secret(origin, state, langs, "secret_agent_stop")
    return mode


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="With two files, the first is the previous snapshot.",
    )
    ap.add_argument("files", nargs="*", metavar="SCHEDULE",
                    help="one export to review, or two to compare (previous first)")
    ap.add_argument("--secret", "--secreto", dest="secret", nargs="?", const="run",
                    choices=["run", "on", "off", "ask"], metavar="on|off|ask",
                    help="alone: run in secret mode (experimental): the agent reads only a coded "
                         "copy, in a work folder. With on, off or ask: store the preference and exit")
    ap.add_argument("--free", "--livre", dest="free", action="store_true",
                    help="run in free mode explicitly: whatever an agent reads goes to its provider")
    ap.add_argument("--config", action="store_true",
                    help="print the stored mode preference and exit")
    ap.add_argument("--outdir", help="where to write the report (default: next to the input)")
    ap.add_argument("--threshold-days", type=int, default=run_checks.DEFAULT_THRESHOLD_DAYS,
                    help="the E and C threshold, in calendar days (default 30)")
    ap.add_argument("--tolerance-days", type=float, default=run_checks.DEFAULT_TOLERANCE_DAYS,
                    help="the G tolerance, in days (default 1)")
    ap.add_argument("--quiet", action="store_true", help="write files without the console summary")
    ap.add_argument("--group-by", default="wbs",
                    help="field the report groups weight by (default: the top WBS branch)")
    ap.add_argument("--template", help="a customised report template to use instead of the default")
    ap.add_argument("--profile", help="JSON profile with theme and field mappings")
    ap.add_argument("--workdir", help="secret mode: the folder under which the coded work folder "
                                      "is created (default ~/cronoaudit-work)")
    ap.add_argument("--project", help="secret mode: the name that keeps the same codes across "
                                      "versions (default: the folder of the schedule)")
    ap.add_argument("--lang", choices=["en", "pt"],
                    help="force the report language; by default it follows the schedule's own")
    args = ap.parse_args(normalise_mode_args(sys.argv[1:]))

    # ---- the mode comes first: nothing below opens a schedule before it is settled.
    import i18n
    mode_txt = i18n.modes_text(args.lang or cfg_mod.system_lang())
    if args.secret and args.free:
        ap.error(mode_txt["both_flags"])
    if args.secret in cfg_mod.VALUES:
        try:
            path = cfg_mod.set_secret(args.secret)
        except OSError as exc:
            raise SystemExit(mode_txt["set_failed"].format(path=cfg_mod.config_path(), error=exc))
        print(describe_config(cfg_mod.load(), mode_txt))
        print("  " + mode_txt["set_done"].format(path=path))
        if args.files:
            print(mode_txt["set_no_run"])
        return
    if args.config:
        print(describe_config(cfg_mod.load(), mode_txt))
        return
    if not args.files:
        ap.error(mode_txt["no_files"])
    mode = settle_mode(args, args.lang)

    if mode == "secret":
        import secret_mode
        raise SystemExit(secret_mode.run(args))
    analyse(args)


def analyse(args, outdir=None) -> list:
    """The analysis itself, the same in both modes. Returns the models it read.

    Secret mode calls this with `outdir` in the vault: the engine runs on the real
    data exactly as in free mode, and only what it wrote is coded afterwards.
    """
    if len(args.files) > 2:
        raise SystemExit("Pass one file to review, or two to compare. More than two is ambiguous.")

    for f in args.files:
        if not os.path.exists(f):
            raise SystemExit(f"{f}: no such file")

    outdir = outdir or args.outdir or os.path.dirname(os.path.abspath(args.files[-1]))
    os.makedirs(outdir, exist_ok=True)

    profile = prof_mod.load(args.profile)
    theme = {k: v for k, v in (profile.get("theme") or {}).items() if v}
    grouping = args.group_by if args.group_by != "wbs" else (profile.get("grouping") or "wbs")
    template = args.template or profile.get("template")
    lang = args.lang or profile.get("lang")
    if args.profile:
        args.threshold_days = profile.get("threshold_days", args.threshold_days)
        args.tolerance_days = profile.get("tolerance_days", args.tolerance_days)

    models = [load(f) for f in args.files]

    if len(models) == 1:
        do_review(models[0], args.files[0], outdir, args.threshold_days,
                  args.tolerance_days, args.quiet, theme, grouping, template, lang,
                  profile=profile)
        return models

    prev_path, curr_path = args.files
    prev, curr = models

    # The comparison runs first so the forensics of the current delivery can use
    # its readings; the review of the current file is still printed first, because
    # a comparison between two files that do not each hold together is a
    # comparison of two wrong answers.
    res = compare_snapshots.compare(prev, curr)
    if not args.quiet:
        print("=== Review of the current delivery ===\n")
    rev = do_review(curr, curr_path, outdir, args.threshold_days, args.tolerance_days,
                    args.quiet, theme, grouping, template, lang, previous=prev, cycle=res,
                    profile=profile)
    base = os.path.join(outdir, f"{stem(prev_path)}--to--{stem(curr_path)}-cycle")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    import i18n
    detected = i18n.detect(curr)
    cycle_payload = report_data.build_cycle(res, theme=theme, lang=lang, detected=detected,
                                            deadlines=(rev or {}).get("_deadlines"))
    with open(base + "-readings.json", "w", encoding="utf-8") as fh:
        # The rule-built sentences the cycle report shows, section by section, so
        # an assistant can quote them instead of composing its own.
        json.dump({"lang": cycle_payload["lang"], "readings": cycle_payload["readings"]},
                  fh, indent=2, ensure_ascii=False)
    report_html.write(cycle_payload, base + ".html", template)
    if not args.quiet:
        print("\n=== Cycle comparison ===\n")
        print(compare_snapshots.report(res))
        print()
    print(f"  report   {base}.html")
    print(f"  data     {base}.json")
    return models


if __name__ == "__main__":
    main()
