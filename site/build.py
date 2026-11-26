#!/usr/bin/env python3
"""Build the cronoaudit website: docs/index.html (English) and docs/pt/index.html (Portuguese).

    python3 site/build.py

Both pages come from one template (site/template.html) and one strings file
(site/strings.json), so the two languages stay parallel: a key missing in one of them
stops the build. The version is read from .claude-plugin/plugin.json and the image sizes
from the PNG files themselves. Standard library only.

The site makes no third-party request: fonts, styles, script, images and video are all
under docs/. The build checks that too.
"""
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = ROOT / "docs"
IMAGES = ["hero", "past-rewritten", "progress", "deadlines", "ask", "how-it-works", "install"]


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[12:16] != b"IHDR":
        raise SystemExit(f"not a PNG: {path}")
    return struct.unpack(">II", head[16:24])


def fill(text, values):
    """Replace {{key}} until none is left; an unknown key stops the build."""
    for _ in range(4):
        def sub(m):
            if m.group(1) not in values:
                raise SystemExit(f"no string for {{{{{m.group(1)}}}}}")
            return str(values[m.group(1)])
        new = re.sub(r"\{\{([\w-]+)\}\}", sub, text)
        if new == text:
            return new
        text = new
    raise SystemExit("strings refer to each other in a loop")


def main():
    strings = json.loads((HERE / "strings.json").read_text(encoding="utf-8"))
    template = (HERE / "template.html").read_text(encoding="utf-8")
    version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    if set(strings["en"]) != set(strings["pt"]):
        raise SystemExit("en and pt differ in keys: " + ", ".join(sorted(set(strings["en"]) ^ set(strings["pt"]))))

    for lang, out, root in (("en", DOCS / "index.html", ""), ("pt", DOCS / "pt" / "index.html", "../")):
        v = dict(strings["shared"])
        v.update(strings[lang])
        v.update(lang=lang, root=root, version=version)
        for name in IMAGES:
            w, h = png_size(DOCS / "img" / lang / f"{name}.png")
            v[f"w_{name}"], v[f"h_{name}"] = w, h
        # the reader's own language first
        pdf = lambda kind, l: f'<a href="{root}{kind}/{kind}-{l}.pdf">{v["pdf_" + l]}</a>'
        order = ["en", "pt"] if v["pdf_first"] == "en" else ["pt", "en"]
        v["guide_links"] = "".join(pdf("guia", l) for l in order)
        v["manual_links"] = "".join(pdf("manual", l) for l in order)
        html = fill(template, v)
        # nothing on the page may be loaded from another site (links to follow are fine)
        loaded = re.findall(r'<(?:img|source|video|script|link)\b[^>]*?\b(?:src|href|poster)="(https?://[^"]+)"', html)
        loaded = [u for u in loaded if not re.search(r'rel="(?:canonical|alternate)"', html[html.find(u) - 200:html.find(u)])]
        if loaded:
            raise SystemExit("third-party request on the page: " + ", ".join(loaded))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"{out.relative_to(ROOT)}  {len(html.encode('utf-8'))} bytes")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
