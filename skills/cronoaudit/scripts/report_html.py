#!/usr/bin/env python3
"""Inject a report payload into the HTML template.

Same contract as a mature in-tool implementation: the template carries a
`/*DATA*/` marker and this module replaces it with the payload. Presentation lives
in the template, so an organisation restyles the report by editing HTML and CSS,
never Python -- and the same payload can feed a spreadsheet or a dashboard instead.

Template lookup order, so a customised copy always wins over the shipped one:
    1. --template, when given
    2. CRONOAUDIT_TEMPLATE in the environment
    3. templates/report.custom.html   (yours; an update replaces the skill folder, so keep a copy
                                       outside it and pass --template or the profile's template)
    4. templates/report.html          (shipped default)
"""
from __future__ import annotations

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")
MARKER = "/*DATA*/"


def find_template(explicit: str | None = None) -> str:
    for candidate in (
        explicit,
        os.environ.get("CRONOAUDIT_TEMPLATE"),
        os.path.join(TEMPLATES, "report.custom.html"),
        os.path.join(TEMPLATES, "report.html"),
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    raise SystemExit(
        f"No report template found. Expected one at {os.path.join(TEMPLATES, 'report.html')}"
    )


def write(payload: dict, out_path: str, template: str | None = None) -> str:
    tpl_path = find_template(template)
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()
    if MARKER not in tpl:
        raise SystemExit(
            f"{tpl_path}: the {MARKER} marker is missing, so there is nowhere to put the "
            "data. Keep the marker when you customise the template."
        )
    # The payload is injected as a JavaScript literal. `</script>` inside a string
    # would end the script element early, so it is escaped; the JSON stays valid.
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    # The marker sits where a value goes, and the template keeps a `null` after it
    # so the file is still valid JavaScript when opened un-filled. Both have to be
    # consumed together: replacing only the comment leaves `= {...} null;`, which is
    # a syntax error, and a syntax error here renders a blank page rather than
    # failing loudly. Caught exactly that way once.
    # A function replacement, never the string: re.sub would read backslash
    # sequences in the JSON as escapes, turning "\n" inside a synthesis into a
    # real line break and breaking the script. It stayed hidden until the first
    # injected text carried a paragraph break.
    filled, count = re.subn(
        re.escape(MARKER) + r"\s*null", lambda _m: blob, tpl, count=1
    )
    if count == 0:
        filled = tpl.replace(MARKER, blob, 1)

    # The browser tab and the document language are read before any script runs
    # (and by whoever prints or bookmarks the file), so they are written into the
    # markup itself rather than left to the renderer. A function replacement, for
    # the same backslash reason as above.
    if payload.get("page_title"):
        tab = "<title>" + html.escape(str(payload["page_title"])) + "</title>"
        filled = re.sub(r"<title>.*?</title>", lambda _m: tab, filled, count=1, flags=re.S)
    if payload.get("lang"):
        tag = '<html lang="' + html.escape(str(payload["lang"])) + '">'
        filled = re.sub(r"<html lang=\"[^\"]*\">", lambda _m: tag, filled, count=1)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(filled)
    return out_path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Inject a report payload into the template")
    ap.add_argument("payload_json")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--template")
    a = ap.parse_args()
    with open(a.payload_json, encoding="utf-8") as fh:
        print(write(json.load(fh), a.out, a.template))
