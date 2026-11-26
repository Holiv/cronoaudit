#!/usr/bin/env python3
"""Check the printed guide against its rules. Needs pdftotext and pdfinfo (poppler).

    python3 docs/guia/verify.py

For each edition: the page count, no personal path, no word the guide must not use,
no dash in the middle of a sentence, and every engine reading present word for word.
Activity and group names of the fictitious example carry dashes of their own
("Imprimação — Seg. 1"); they are data, so they are removed before the dash check.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DASHES = "—–"


def strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)
    elif isinstance(node, str):
        yield node


def squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def bare(text: str) -> str:
    """Without spaces or hyphens: pdftotext joins and splits words at line ends."""
    return re.sub(r"[\s-]+", "", text)


def check(lang: str) -> list:
    pdf = os.path.join(HERE, f"guia-{lang}.pdf")
    problems = []
    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, check=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    if not 16 <= pages <= 28:
        problems.append(f"{pages} pages, outside 16 to 28")
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    flat = squeeze(subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout)
    for needle in ("/Users/", "/home/", "/private/", "/var/folders", "C:\\Users"):
        if needle in text:
            problems.append(f"path fragment {needle!r} appears")
    for word in ("bloqueio", "bloquei", "furar"):
        if re.search(word, text, re.I):
            problems.append(f"the word {word!r} appears")

    # Names of the example, longest first, in the forms the engine prints them.
    data = os.path.join(HERE, "dados", lang)
    names = set()
    for f in os.listdir(data):
        if f.endswith(".json") and not f.startswith("coded-"):
            for s in strings(json.load(open(os.path.join(data, f), encoding="utf-8"))):
                if any(d in s for d in DASHES) and len(s) < 120:
                    names.add(squeeze(s))
    rest = flat
    for name in sorted(names, key=len, reverse=True):
        rest = rest.replace(name, " ")
    left = [m.start() for m in re.finditer(f"[{DASHES}]", rest)]
    for pos in left[:8]:
        problems.append("dash outside an example name: ..." + rest[max(0, pos - 50):pos + 30] + "...")
    in_names = sum(flat.count(d) for d in DASHES) - len(left)

    # Every reading quoted in the content is in the PDF word for word.
    content = open(os.path.join(HERE, f"content-{lang}.html"), encoding="utf-8").read()
    quoted = found = 0
    flat_bare = bare(flat)
    for kind, which, section, index in re.findall(r"\{\{(R|C) (\w+) (\w+) (\d+)\}\}", content):
        src = ("coded-" if kind == "C" else "") + which + "-readings.json"
        sentence = bare(json.load(open(os.path.join(data, src), encoding="utf-8"))["readings"][section][int(index)])
        quoted += 1
        if sentence in flat_bare:
            found += 1
        else:
            problems.append(f"reading not found word for word: {which}.{section}[{index}]")
    print(f"guia-{lang}.pdf: {pages} pages, {found} of {quoted} engine readings found word for word, "
          f"{in_names} dashes, all inside example names")
    return problems


def main():
    bad = 0
    for lang in ("pt", "en"):
        if not os.path.exists(os.path.join(HERE, f"guia-{lang}.pdf")):
            continue
        for p in check(lang):
            bad += 1
            print(f"  PROBLEM ({lang}): {p}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
