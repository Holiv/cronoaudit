#!/usr/bin/env python3
"""Secret mode, the way back: decode on this machine. EXPERIMENTAL.

    python3 secret_decode.py finish [WORKDIR] [--no-open]
        Decode the coded report(s) of a work folder, including the synthesis the
        agent injected, into the real report: written in the vault and beside the
        original, then opened in the browser. Prints counts only, never a name, a
        value, a date or a path, so it is safe for the agent to run it.

    python3 secret_decode.py text [WORKDIR] [FILE]
        Translate text written in codes (an agent's answer pasted on stdin, or a
        file) into real names, dates and money, on the person's screen. The PERSON
        runs this, in their own terminal. An agent must never run it: its output
        would go to the agent's provider. It refuses to run inside an agent, and
        the Claude Code guard blocks it too.

WORKDIR defaults to the current folder; it is the folder review.py --secret printed.

`finish` checks lesson 2 of the design on every run: the decoded report must equal
the engine's own real output, value for value. When it does not, the engine's real
output is written instead and the number of differing values is said.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import cronoaudit_config as cfg_mod  # noqa: E402
import inject_narrative  # noqa: E402
import report_html  # noqa: E402
import secret_codec as codec_mod  # noqa: E402
import secret_mode  # noqa: E402


def load_run(workdir: str):
    with open(os.path.join(workdir, secret_mode.MANIFEST), encoding="utf-8") as fh:
        manifest = json.load(fh)
    run_id = str(manifest["run"])
    if not run_id.isalnum():
        raise SystemExit("cronoaudit: this manifest does not name a run")
    vault_run = os.path.join(secret_mode.vault_dir(), run_id)
    with open(os.path.join(vault_run, "back.json"), encoding="utf-8") as fh:
        codec = codec_mod.Codec.from_back_table(json.load(fh))
    with open(os.path.join(vault_run, "run.json"), encoding="utf-8") as fh:
        run = json.load(fh)
    return manifest, vault_run, run, codec


def decode_payload(codec, coded: dict, real: dict) -> dict:
    """The coded payload back to the real one, narrative included."""
    has = "narrative" in coded
    narrative = coded.pop("narrative", None)
    decoded = codec.decode_obj(coded)
    for path in codec_mod.LEGIBILITY["withheld"]:
        codec_mod.restore(decoded, real, path)
    if isinstance(narrative, dict):
        from datetime import datetime
        when = datetime.now().strftime("%d/%m/%Y %H:%M" if codec.lang == "pt" else "%Y-%m-%d %H:%M")
        decoded["narrative"] = {**narrative,
                                "text": codec.decode_text(narrative.get("text") or "", narrative=True),
                                "when": narrative.get("when") or when}
    elif has:
        decoded["narrative"] = narrative
    return decoded


def count_leaves(a, b) -> tuple:
    """(equal, different) leaf values between two JSON structures."""
    if isinstance(a, dict) and isinstance(b, dict):
        eq = df = 0
        for k in set(a) | set(b):
            if k in a and k in b:
                e, d = count_leaves(a[k], b[k])
                eq, df = eq + e, df + d
            else:
                df += 1
        return eq, df
    if isinstance(a, list) and isinstance(b, list):
        eq, df = 0, abs(len(a) - len(b))
        for x, y in zip(a, b):
            e, d = count_leaves(x, y)
            eq, df = eq + e, df + d
        return eq, df
    same = (a == b) and type(a) is type(b)
    return (1, 0) if same else (0, 1)


def finish(workdir: str, open_it: bool = True, beside_original: bool = True) -> dict:
    manifest, vault_run, run, codec = load_run(workdir)
    result = {"reports": 0, "equal": 0, "different": 0, "written": []}
    for coded_name, real_name in (run.get("html") or {}).items():
        coded_path = os.path.join(workdir, coded_name)
        if not os.path.exists(coded_path):
            continue
        with open(coded_path, encoding="utf-8") as fh:
            coded = inject_narrative.extract(fh.read())
        with open(os.path.join(vault_run, "real", real_name), encoding="utf-8") as fh:
            real = inject_narrative.extract(fh.read())
        decoded = decode_payload(codec, dict(coded), real)
        narrative = decoded.pop("narrative", None)
        real = {k: v for k, v in real.items() if k != "narrative"}
        eq, df = count_leaves(decoded, real)
        result["equal"] += eq
        result["different"] += df
        final = decoded if df == 0 else json.loads(json.dumps(real))
        if narrative is not None:
            final["narrative"] = narrative
        targets = [os.path.join(vault_run, real_name)]
        if beside_original:
            targets.append(os.path.join(os.path.dirname(run["files"][-1]), real_name))
        for t in targets:
            try:
                report_html.write(final, t, run.get("template"))
                result["written"].append(t)
            except OSError:
                pass
        result["reports"] += 1
    if open_it and result["written"]:
        first = [p for p in result["written"] if not p.startswith(vault_run)] or result["written"]
        try:
            webbrowser.open(Path(first[0]).resolve().as_uri())
        except Exception:
            pass
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["finish", "text"])
    ap.add_argument("workdir", nargs="?", default=".")
    ap.add_argument("file", nargs="?", help="text: a file to translate instead of stdin")
    ap.add_argument("--no-open", action="store_true", help="finish: do not open the browser")
    ap.add_argument("--vault-only", action="store_true",
                    help="finish: write the decoded report only in the vault, not beside the original")
    args = ap.parse_args()
    workdir = os.path.abspath(args.workdir)
    if not os.path.exists(os.path.join(workdir, secret_mode.MANIFEST)):
        print("cronoaudit: this is not a secret-mode work folder (no manifest here).", file=sys.stderr)
        return 1

    if args.action == "text":
        import review
        var = review.agent_environment()
        if var:
            print(f"cronoaudit: `text` prints real names and refuses to run inside an agent ({var} is "
                  "set). Run it in your own terminal.", file=sys.stderr)
            return 3
        _m, _v, _r, codec = load_run(workdir)
        if args.file:
            with open(args.file, encoding="utf-8") as fh:
                src = fh.read()
        else:
            if sys.stdin.isatty():
                print("Paste the coded text, then Ctrl-D (Ctrl-Z Enter on Windows):", file=sys.stderr)
            src = sys.stdin.read()
        # A Ctrl-Z typed at the end of a line on Windows arrives as a character, not as
        # the end of the input; it is a keystroke, not text.
        src = src.replace("\x1a", "")
        print(codec.decode_text(src, narrative=True))
        return 0

    try:
        r = finish(workdir, open_it=not args.no_open, beside_original=not args.vault_only)
    except Exception as exc:
        print(f"cronoaudit: decoding failed ({type(exc).__name__}). Nothing was shown.", file=sys.stderr)
        return 1
    if r["different"]:
        print(f"cronoaudit: {r['reports']} report(s) decoded on this machine. CHECK FAILED: "
              f"{r['different']} value(s) did not decode to the engine's output, so the engine's real "
              f"output was written instead (with the synthesis).")
        return 1
    print(f"cronoaudit: {r['reports']} report(s) decoded on this machine; check passed, "
          f"{r['equal']} value(s) equal to the engine's own output. Written "
          f"{'in the vault' if args.vault_only else 'beside the original'}"
          f"{'' if args.no_open else ' and opened in the browser'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
