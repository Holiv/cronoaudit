#!/usr/bin/env python3
"""Check the built website: every internal link and asset resolves, every anchor exists,
every image has alt text, and nothing is loaded from another site.

    python3 site/check.py

Reads docs/index.html and docs/pt/index.html from disk. Standard library only.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

DOCS = Path(__file__).resolve().parent.parent / "docs"
SITE = "https://holiv.github.io/cronoaudit/"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.problems = [], set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "img" and not (a.get("alt") or "").strip():
            self.problems.append(f"image with no alt text: {a.get('src')}")
        for key in ("href", "src", "poster"):
            if key in a:
                self.refs.append((tag, key, a[key], a.get("rel", "")))
        if tag == "meta" and a.get("property") in ("og:image", "og:url") or a.get("name") == "twitter:image":
            self.refs.append((tag, "content", a.get("content", ""), "meta"))


def check(page_path):
    page = Page()
    page.feed(page_path.read_text(encoding="utf-8"))
    problems = list(page.problems)
    for tag, key, ref, rel in page.refs:
        u = urlparse(ref)
        if u.scheme in ("http", "https"):
            if ref.startswith(SITE):                       # our own absolute URLs must exist in docs/
                target = DOCS / unquote(ref[len(SITE):].split("#")[0])
                if target.is_dir():
                    target = target / "index.html"
                if not target.exists():
                    problems.append(f"own URL with no file: {ref}")
            elif tag != "a":                               # only links to follow may leave the site
                problems.append(f"third-party request: <{tag} {key}={ref}>")
            continue
        if u.scheme:                                       # mailto: and the like
            continue
        if u.path:
            target = (page_path.parent / unquote(u.path)).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                problems.append(f"missing file: {ref}")
            elif DOCS.resolve() not in target.parents:
                problems.append(f"outside docs/: {ref}")
        elif u.fragment and u.fragment not in page.ids:
            problems.append(f"missing anchor: {ref}")
    return len(page.refs), problems


def main():
    bad = 0
    for p in (DOCS / "index.html", DOCS / "pt" / "index.html"):
        n, problems = check(p)
        print(f"{p.relative_to(DOCS.parent)}: {n} references, {len(problems)} problem(s)")
        for x in problems:
            print("  " + x)
        bad += len(problems)
    # the stylesheet's own files
    css = (DOCS / "assets" / "site.css").read_text(encoding="utf-8")
    for ref in re.findall(r'url\("?([^")]+)"?\)', css):
        if ref.startswith("http") or not (DOCS / "assets" / ref).exists():
            print(f"  site.css: bad url {ref}")
            bad += 1
    if not (DOCS / ".nojekyll").exists():
        print("  docs/.nojekyll is missing")
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
