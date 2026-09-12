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
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compare_snapshots  # noqa: E402
import parse_mspdi  # noqa: E402
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


def do_review(model, path, outdir, threshold, tolerance, quiet) -> dict:
    res = run_checks.run(model, threshold, tolerance)
    base = os.path.join(outdir, f"{stem(path)}-review")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    report_html.write(res, base + ".html", "review")
    if not quiet:
        print(run_checks.report(res))
        print()
    print(f"  report   {base}.html")
    print(f"  data     {base}.json")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="With two files, the first is the previous snapshot.",
    )
    ap.add_argument("files", nargs="+", metavar="SCHEDULE",
                    help="one export to review, or two to compare (previous first)")
    ap.add_argument("--outdir", help="where to write the report (default: next to the input)")
    ap.add_argument("--threshold-days", type=int, default=run_checks.DEFAULT_THRESHOLD_DAYS,
                    help="the E and C threshold, in calendar days (default 30)")
    ap.add_argument("--tolerance-days", type=float, default=run_checks.DEFAULT_TOLERANCE_DAYS,
                    help="the G tolerance, in days (default 1)")
    ap.add_argument("--quiet", action="store_true", help="write files without the console summary")
    args = ap.parse_args()

    if len(args.files) > 2:
        raise SystemExit("Pass one file to review, or two to compare. More than two is ambiguous.")

    for f in args.files:
        if not os.path.exists(f):
            raise SystemExit(f"{f}: no such file")

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.files[-1]))
    os.makedirs(outdir, exist_ok=True)

    models = [load(f) for f in args.files]

    if len(models) == 1:
        do_review(models[0], args.files[0], outdir,
                  args.threshold_days, args.tolerance_days, args.quiet)
        return

    prev_path, curr_path = args.files
    prev, curr = models

    # Review the current delivery first. A comparison between two files that do not
    # each hold together is a comparison of two wrong answers, and the network
    # findings decide whether the forecast dates in the comparison mean anything.
    if not args.quiet:
        print("=== Review of the current delivery ===\n")
    do_review(curr, curr_path, outdir, args.threshold_days, args.tolerance_days, args.quiet)

    res = compare_snapshots.compare(prev, curr)
    base = os.path.join(outdir, f"{stem(prev_path)}--to--{stem(curr_path)}-cycle")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    report_html.write(res, base + ".html", "comparison")
    if not args.quiet:
        print("\n=== Cycle comparison ===\n")
        print(compare_snapshots.report(res))
        print()
    print(f"  report   {base}.html")
    print(f"  data     {base}.json")


if __name__ == "__main__":
    main()
