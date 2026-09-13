#!/usr/bin/env python3
"""Assemble the manual: cover, front matter, table of contents, chapters.

    python3 build.py            # writes manual-pt.html and manual-en.html beside this file

Content lives in content-<lang>.html as plain chapter sections; this script adds
the cover, the colophon, a contents list generated from the headings, and the
shared stylesheet. Then topdf.js prints each to PDF with running heads and page
numbers.
"""
from __future__ import annotations

import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = open(os.path.join(HERE, "..", "..", "skills", "cronoaudit", "VERSION")).read().strip()

TEXT = {
    "pt": {
        "title_html": "crono<em>audit</em>",
        "kicker": "Manual técnico · versão {v}",
        "sub": "Análise crítica de cronograma, do arquivo ao veredito. Como instalar, como usar, como ler o relatório e como reproduzir cada número.",
        "author": "Autor", "author_v": "Helton da Silva de Oliveira",
        "format": "Formato", "format_v": "Agent Skill · Apache 2.0",
        "edition": "Edição", "edition_v": "Português",
        "fig_ref": "LINHA DE BASE · REFERÊNCIA", "fig_a": "previsto", "fig_b": "realizado",
        "fig_other": "outra referência: a mesma medição, outro resultado",
        "fig_quote": "a diferença só existe se a referência for a mesma",
        "toc": "Sumário",
        "colophon_h": "Sobre este manual",
        "colophon": [
            "Este manual acompanha a versão {v} da cronoaudit. Ele foi escrito para quem recebe um cronograma e precisa dizer se aquilo é verdade, e não assume que o leitor conheça os conceitos: cada capítulo começa pelo conceito, depois mostra o que a ferramenta faz com ele.",
            "Todos os exemplos usam os cronogramas sintéticos que acompanham a ferramenta. Nenhum dado real de contrato, contratada ou pessoa aparece aqui.",
            "A ferramenta segue o formato aberto Agent Skills e funciona com qualquer agente que o leia, e também sem agente nenhum. O código-fonte, a licença e a versão mais recente estão em github.com/Holiv/cronoaudit.",
        ],
        "running": "cronoaudit · manual técnico",
    },
    "en": {
        "title_html": "crono<em>audit</em>",
        "kicker": "Technical manual · version {v}",
        "sub": "Schedule critical analysis, from the file to the verdict. How to install, how to use, how to read the report, and how to reproduce every figure.",
        "author": "Author", "author_v": "Helton da Silva de Oliveira",
        "format": "Format", "format_v": "Agent Skill · Apache 2.0",
        "edition": "Edition", "edition_v": "English",
        "fig_ref": "BASELINE · REFERENCE", "fig_a": "planned", "fig_b": "actual",
        "fig_other": "another reference: the same measurement, another result",
        "fig_quote": "the difference only exists if the reference is the same",
        "toc": "Contents",
        "colophon_h": "About this manual",
        "colophon": [
            "This manual accompanies version {v} of cronoaudit. It was written for whoever receives a schedule and has to say whether it is true, and it does not assume the reader knows the concepts: every chapter starts from the concept, then shows what the tool does with it.",
            "Every example uses the synthetic schedules shipped with the tool. No real contract, contractor or person appears here.",
            "The tool follows the open Agent Skills format and works with any agent that reads it, and with no agent at all. Source, licence and the latest version are at github.com/Holiv/cronoaudit.",
        ],
        "running": "cronoaudit · technical manual",
    },
}

COVER_SVG = """<svg viewBox="0 0 520 150" aria-hidden="true">
  <line x1="10" y1="120" x2="510" y2="120" stroke="#B3261E" stroke-width="2"/>
  <text x="14" y="136" font-family="Source Code Pro" font-size="9" fill="#B3261E">{fig_ref}</text>
  <line x1="120" y1="120" x2="120" y2="40" stroke="#17191C" stroke-width="1"/><circle cx="120" cy="40" r="3.5" fill="#17191C"/>
  <text x="128" y="44" font-family="Source Code Pro" font-size="9" fill="#17191C">{fig_a}</text>
  <line x1="330" y1="120" x2="330" y2="70" stroke="#17191C" stroke-width="1"/><circle cx="330" cy="70" r="3.5" fill="#17191C"/>
  <text x="338" y="74" font-family="Source Code Pro" font-size="9" fill="#17191C">{fig_b}</text>
  <line x1="10" y1="96" x2="510" y2="96" stroke="#B3261E" stroke-width="1" stroke-dasharray="3 4" opacity=".7"/>
  <text x="14" y="92" font-family="Source Code Pro" font-size="8" fill="#B3261E" opacity=".8">{fig_other}</text>
  <path d="M120 40 L330 70" stroke="#6B6E74" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="180" y="42" font-family="Fraunces" font-style="italic" font-size="11" fill="#6B6E74">{fig_quote}</text>
</svg>"""


def slugify(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^\w]+", "-", s.lower()).strip("-")
    return s[:60]


def build(lang: str) -> str:
    T = {k: (v.format(v=VERSION) if isinstance(v, str) else [x.format(v=VERSION) for x in v])
         for k, v in TEXT[lang].items()}
    # Content may be split into numbered parts to keep files manageable.
    import glob
    parts = sorted(glob.glob(os.path.join(HERE, f"content-{lang}-*.html")))
    if not parts and os.path.exists(os.path.join(HERE, f"content-{lang}.html")):
        parts = [os.path.join(HERE, f"content-{lang}.html")]
    content = "\n".join(open(p, encoding="utf-8").read() for p in parts)

    # Number chapters and give every h1/h2 an id, collecting the contents list.
    toc = []
    chapter = 0
    section = 0

    def h1(m):
        nonlocal chapter, section
        chapter += 1
        section = 0
        title = m.group(2)
        sid = f"ch{chapter}"
        toc.append(("", f"{chapter}", title, sid))
        return f'<p class="chno">{chapter}</p><h1 class="ch" id="{sid}">{title}</h1>'

    def h2(m):
        nonlocal section
        section += 1
        title = m.group(2)
        sid = f"ch{chapter}-{section}"
        toc.append(("sub", f"{chapter}.{section}", title, sid))
        return f'<h2 id="{sid}">{title}</h2>'

    # One pass over both levels, so section numbers follow the chapter they sit in.
    def heading(m):
        return h1(m) if m.group(1) == "1" else h2(m)

    content = re.sub(r"<h([12])>(.*?)</h\1>", heading, content, flags=re.S)

    toc_html = "\n".join(
        f'<li class="{cls}"><span class="n">{num}</span><a href="#{sid}">{title}</a></li>'
        for cls, num, title, sid in toc
    )
    colophon = "\n".join(f"<p>{html.escape(p)}</p>" for p in T["colophon"])
    cover_svg = COVER_SVG.format(**T)

    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>cronoaudit — {'manual técnico' if lang == 'pt' else 'technical manual'} {VERSION}</title>
<meta name="author" content="{T['author_v']}">
<link rel="stylesheet" href="style.css">
</head><body>
<div class="cover">
  <p class="kicker">{html.escape(T['kicker'])}</p>
  <h1>{T['title_html']}</h1>
  <p class="sub">{html.escape(T['sub'])}</p>
  {cover_svg}
  <div class="meta">
    <span>{T['author']}<b>{T['author_v']}</b></span>
    <span>{T['format']}<b>{T['format_v']}</b></span>
    <span>{T['edition']}<b>{T['edition_v']}</b></span>
  </div>
</div>
<div class="front">
  <h2>{html.escape(T['colophon_h'])}</h2>
  {colophon}
  <h2 style="margin-top:12mm">{html.escape(T['toc'])}</h2>
  <ol class="toc">
  {toc_html}
  </ol>
</div>
{content}
</body></html>
"""


if __name__ == "__main__":
    for lang in ("pt", "en"):
        import glob
        if not glob.glob(os.path.join(HERE, f"content-{lang}*.html")):
            print(f"skip {lang}: no content-{lang}*.html")
            continue
        out = os.path.join(HERE, f"manual-{lang}.html")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(build(lang))
        print(out)
