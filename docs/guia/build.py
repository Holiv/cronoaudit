#!/usr/bin/env python3
"""Assemble the illustrated guide and print it to PDF.

    python3 docs/guia/build.py              # guia-pt.html, guia-en.html, then the PDFs
    python3 docs/guia/build.py --html-only  # stop before Chrome

The pages are written by hand in content-<lang>.html, one <section class="page"> per
sheet. Everything that is a fact about the example comes from files, not from the
prose: capturas/ holds what the terminal printed, dados/ the engine's JSON, img/ the
captures of the engine's own report. capture.sh produces the three. Placeholders in
the content pull from them:

    {{R cycle c1 0}}    a reading of the engine, verbatim (file, section, index)
    {{C cycle c1 3}}    the same reading in the coded copy of a secret run
    {{D 0}} {{DC 0}}    an item of "what to ask the contractor", real and coded
    {{term name}}       a terminal panel (TERMS below says which lines are shown)
    {{svg name}}        a figure drawn from the JSON
    {{html name}}       a block built from the JSON (tiles, lists, cards)
    {{img name url [height] [offset]}}  a capture of the report, in a browser frame
    {{pg id}}           the page number of the section with that id
    {{toc}} {{V}} {{run}}

The PDF needs Node with puppeteer-core (NODE_PATH) and Chrome, as the manual does.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = open(os.path.join(HERE, "..", "..", "skills", "cronoaudit", "VERSION")).read().strip()

INK, INK2, INK3, REF, LINE, GRID, WASH = "#17191C", "#3F434A", "#6B6E74", "#B3261E", "#CFC9BC", "#ECE7DB", "#F1EDE2"
MONO, SERIF = "Source Code Pro", "Fraunces"

esc = html.escape

# ---------------------------------------------------------------------------
# Words used by the generated parts. The prose lives in content-<lang>.html.
# ---------------------------------------------------------------------------
L = {
    "pt": {
        "running": "cronoaudit · guia ilustrado · {v}",
        "real": "captura real", "eng": "leitura do motor", "ilus": "ilustração",
        "cut": "⋯ {n} linhas cortadas ⋯", "cut1": "⋯ 1 linha cortada ⋯",
        "row": "linha", "planted": "plantado nº {n}",
        "months": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
        "ms": {4: "Terraplenagem concluída", 5: "Tráfego no Segmento 1", 7: "Tráfego no Segmento 3",
               6: "Tráfego no Segmento 2", 8: "Tráfego no Segmento 4", 9: "Viaduto V-01 concluído",
               10: "Recebimento provisório"},
        "ms_head": ["marco", "margem", "com P80"], "ms_finish": "tendência", "ms_deadline": "data limite",
        "ms_p80": "tendência com o escorregamento P80", "days": "d",
        "seg": "Segmento", "viaduct": "Viaduto V-01 · km 27+400", "whole": "na obra inteira",
        "status": "data de status", "planned": "previsto", "earned": "realizado",
        "wf": ["rev03", "avanço por atividade", "atividade removida", "orçamento alterado", "rev04"],
        "wf_unit": "pontos percentuais",
        "chain_y": "dias contra a linha de base", "chain_origin": "origem", "chain_amp": "duração 12 → 20",
        "chain_ms": "marco", "chain_started": "iniciada", "chain_not": "não iniciada",
        "look": ["o plano prevê", "o ritmo praticado entrega"], "rain_res": "meses com reserva de chuva no calendário",
        "rain_other": "demais meses", "rain_axis": "custo remanescente por mês",
        "q_of": "{a} de {b}", "q_lim": "limite {t}%", "q_min": "mínimo {t}", "q_pass": "atende", "q_fail": "não atende",
        "q_none": "sem limiar", "q_nc": "não calculável de um arquivo",
        "rev_a": "rev03 · 30/09/2026", "rev_b": "rev04 · 30/10/2026",
        "cover": ["linha 157", "duração 12 → 20 dias úteis", "linha 29", "término real reescrito",
                  "linha 119", "removida, estava a 100%", "linha 57", "nova na rev04",
                  "linha 63", "término 53 dias depois", "REV03 · REFERÊNCIA"],
        "ba": {
            "f_actual": "término real", "f_state": "situação", "f_bl": "término da linha de base",
            "f_dur": "duração", "f_con": "restrição", "f_link": "vínculo", "f_budget": "orçamento",
            "f_float": "folga total", "f_finish": "término",
            "gone": "não existe mais", "absent": "não existia", "moved": "movido +{d} dias", "kept": "como aprovada",
            "wd": "{n} dias úteis", "pct": "{p}% concluída", "none": "nenhuma", "exists": "existe", "removed": "retirado",
            "new": "0% · sem início",
        },
    },
    "en": {
        "running": "cronoaudit · illustrated guide · {v}",
        "real": "real capture", "eng": "engine reading", "ilus": "illustration",
        "cut": "⋯ {n} lines cut ⋯", "cut1": "⋯ 1 line cut ⋯",
        "row": "row", "planted": "planted no. {n}",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "ms": {4: "Earthworks complete", 5: "Segment 1 open to traffic", 7: "Segment 3 open to traffic",
               6: "Segment 2 open to traffic", 8: "Segment 4 open to traffic", 9: "Viaduct V-01 complete",
               10: "Provisional acceptance"},
        "ms_head": ["milestone", "margin", "at P80"], "ms_finish": "forecast", "ms_deadline": "deadline",
        "ms_p80": "forecast with the P80 slippage", "days": "d",
        "seg": "Segment", "viaduct": "Viaduct V-01 · km 27+400", "whole": "across the whole job",
        "status": "status date", "planned": "planned", "earned": "earned",
        "wf": ["rev03", "per-activity progress", "removed activity", "budget changed", "rev04"],
        "wf_unit": "percentage points",
        "chain_y": "days against the baseline", "chain_origin": "origin", "chain_amp": "duration 12 → 20",
        "chain_ms": "milestone", "chain_started": "started", "chain_not": "not started",
        "look": ["the plan expects", "the practised rate delivers"], "rain_res": "months with a rain reserve in the calendar",
        "rain_other": "other months", "rain_axis": "remaining cost by month",
        "q_of": "{a} of {b}", "q_lim": "threshold {t}%", "q_min": "minimum {t}", "q_pass": "pass", "q_fail": "fail",
        "q_none": "no threshold", "q_nc": "not computable from one file",
        "rev_a": "rev03 · 2026-09-30", "rev_b": "rev04 · 2026-10-30",
        "cover": ["row 157", "duration 12 → 20 working days", "row 29", "actual finish rewritten",
                  "row 119", "removed, it was at 100%", "row 57", "new in rev04",
                  "row 63", "finish 53 days later", "REV03 · REFERENCE"],
        "ba": {
            "f_actual": "actual finish", "f_state": "state", "f_bl": "baseline finish",
            "f_dur": "duration", "f_con": "constraint", "f_link": "link", "f_budget": "budget",
            "f_float": "total float", "f_finish": "finish",
            "gone": "no longer exists", "absent": "did not exist", "moved": "moved +{d} days", "kept": "as approved",
            "wd": "{n} working days", "pct": "{p}% complete", "none": "none", "exists": "exists", "removed": "removed",
            "new": "0% · not started",
        },
    },
}

# ---------------------------------------------------------------------------
# Terminal panels: which capture, which command was typed, which lines are shown.
# "keep" is 1-based inclusive ranges of the capture; every gap is marked as a cut.
# The command is the one capture.sh ran, with the throwaway HOME written as "~".
# ---------------------------------------------------------------------------
REVIEW = "python3 ~/.claude/skills/cronoaudit/scripts/review.py"
DECODE = "python3 ~/.claude/skills/cronoaudit/scripts/secret_decode.py"
PAIR = "rodovia-ficticia-rev03.xml rodovia-ficticia-rev04.xml"


def lang_flag(lang):
    return " --lang " + lang


TERMS = {
    "install": dict(file="install", title={"pt": "terminal · instalação", "en": "terminal · installation"},
                    cmd=lambda g: ["CRONOAUDIT_EXAMPLE=1 bash install.sh --from ."], keep=[(1, 24)], hl=[13]),
    "cycle": dict(file="cycle", title={"pt": "terminal · ~/cronoaudit-exemplo", "en": "terminal · ~/cronoaudit-exemplo"},
                  cmd=lambda g: [f"{REVIEW} {PAIR} --free{lang_flag(g)}"],
                  keep=[(1, 3), (10, 12), (22, 23), (28, 51), (71, 72)], hl=[12, 38, 43, 51]),
    "question": dict(file="question", title={"pt": "terminal · a pergunta do modo", "en": "terminal · the mode question"},
                     cmd=lambda g: [f"{REVIEW} rodovia-ficticia-rev04.xml{lang_flag(g)}"],
                     keep=[(1, 3), (12, 12), (25, 26)], hl=[1], typed=[2]),
    "refuse": dict(file="refuse", title={"pt": "terminal aberto por um agente", "en": "a terminal started by an agent"},
                   cmd=lambda g: [f"{REVIEW} {PAIR} --secret{lang_flag(g)}"], keep=[(1, 5)], hl=[2]),
    "secret": dict(file="secret", title={"pt": "terminal da pessoa · modo secreto", "en": "the person's terminal · secret mode"},
                   cmd=lambda g: [f"{REVIEW} {PAIR} --secret{lang_flag(g)} --workdir ~/cronoaudit-work"],
                   keep=[(1, 1), (4, 4), (29, 37), (46, 46), (58, 62), (70, 77)], hl=[1, 71]),
    "workdir": dict(file="workdir", title={"pt": "a pasta de trabalho", "en": "the work folder"},
                    cmd=lambda g: ["ls -A1 ~/cronoaudit-work/{run}"], keep=[(1, 15)], hl=[]),
    "decode": dict(file="decoded-answer", title={"pt": "terminal da pessoa · a volta", "en": "the person's terminal · the way back"},
                   cmd=lambda g: [f"{DECODE} text ~/cronoaudit-work/{{run}} < coded-answer-{g}.txt"], keep=[(1, 4)], hl=[]),
    "finish": dict(file="finish", title={"pt": "terminal · o relatório final", "en": "terminal · the final report"},
                   cmd=lambda g: [f"{DECODE} finish --no-open"], keep=[(1, 1)], hl=[1]),
}

TOKEN = re.compile(r"([A-Z]·[0-9a-f]{6}|[dD]\+\d{4}(?:T[\d:]+)?|¤[\d.,]+\d)")


DATE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})")


def whole_dates(text_html: str) -> str:
    """Keep a date on one line; the words are untouched."""
    return DATE.sub(r'<span style="white-space:nowrap">\1</span>', text_html)


def tokens(text_html: str) -> str:
    return TOKEN.sub(r'<span class="tok">\1</span>', text_html)


class Guide:
    def __init__(self, lang: str):
        self.lang = lang
        self.T = L[lang]
        d = os.path.join(HERE, "dados", lang)
        self.j = {os.path.splitext(f)[0]: json.load(open(os.path.join(d, f), encoding="utf-8"))
                  for f in sorted(os.listdir(d)) if f.endswith(".json")}
        self.run = ""
        for line in self.cap("secret"):
            m = re.search(r"~/cronoaudit-work/([0-9a-f]+)", line)
            if m:
                self.run = m.group(1)
                break
        self.pages = {}

    # -- sources ------------------------------------------------------------
    def cap(self, name: str) -> list:
        path = os.path.join(HERE, "capturas", f"{name}-{self.lang}.txt")
        return open(path, encoding="utf-8").read().rstrip("\n").split("\n")

    def num(self, x, nd=2, sign=False) -> str:
        s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
        s = s.replace("-", "−")
        return s.replace(".", ",") if self.lang == "pt" else s

    def money(self, x) -> str:
        s = f"{x:,.0f}"
        return s.replace(",", ".") if self.lang == "pt" else s

    def date(self, iso: str) -> str:
        iso = iso[:10]
        if self.lang == "pt":
            y, m, d = iso.split("-")
            return f"{d}/{m}/{y}"
        return iso

    def reading(self, which, section, index, coded=False) -> str:
        key = ("coded-" if coded else "") + which + "-readings"
        text = esc(self.j[key]["readings"][section][int(index)])
        return tokens(text) if coded else whole_dates(text)

    def demand(self, index, coded=False) -> str:
        key = ("coded-" if coded else "") + "cycle-readings"
        text = esc(self.j[key]["demands"][int(index)]["text"])
        return tokens(text) if coded else whole_dates(text)

    def name(self, row: int) -> str:
        for t in self.j["cycle"]["trend"]:
            if t["id"] == row:
                return t["name"]
        for t in self.j["cycle"]["unmatched"]["inserted"]:
            if t["id"] == row:
                return t["name"]
        raise KeyError(row)

    # -- terminal -----------------------------------------------------------
    def term(self, name: str) -> str:
        spec = TERMS[name]
        lines = self.cap(spec["file"])
        out = []
        for c in spec["cmd"](self.lang):
            out.append(f'<span class="l cmd">{esc(c.replace("{run}", self.run))}</span>')
        last = 0
        for a, b in spec["keep"]:
            b = min(b, len(lines))
            gap = a - last - 1
            # A cut is only worth marking when it drops something other than blank lines.
            dropped = [x for x in lines[last:a - 1] if x.strip()]
            if gap > 0 and dropped:
                label = self.T["cut1"] if len(dropped) == 1 else self.T["cut"].format(n=len(dropped))
                out.append(f'<span class="l cut">{label}</span>')
            for n in range(a, b + 1):
                text = tokens(esc(lines[n - 1]))
                cls = "l"
                if n in spec.get("hl", []):
                    cls += " hl"
                if n in spec.get("typed", []):
                    text = text.replace("&gt; ", '&gt; <span class="typed">', 1) + "</span>"
                out.append(f'<span class="{cls}">{text or " "}</span>')
            last = b
        dropped = [x for x in lines[last:] if x.strip()]
        if dropped:
            label = self.T["cut1"] if len(dropped) == 1 else self.T["cut"].format(n=len(dropped))
            out.append(f'<span class="l cut">{label}</span>')
        title = spec["title"][self.lang]
        return (f'<div class="term"><div class="bar"><i></i><i></i><i></i><span>{esc(title)}</span>'
                f'<b class="mark">{self.T["real"]}</b></div><pre>{"".join(out)}</pre></div>')

    # -- report captures ----------------------------------------------------
    def img(self, name: str, url: str, crop: str = "", shift: str = "") -> str:
        # crop: the visible height; shift: how far down the capture the window starts.
        style = f' style="max-height:{crop}"' if crop else ""
        up = f' style="margin-top:-{shift}"' if shift else ""
        return (f'<div class="browser"><div class="bar"><i></i><i></i><i></i><span class="url">{esc(url)}</span>'
                f'<b class="mark real">{self.T["real"]}</b></div>'
                f'<div class="shot"{style}><img src="img/{name}-{self.lang}.png" alt=""{up}></div></div>')

    # -- figures ------------------------------------------------------------
    # Figures set in half a column are printed smaller, so their lettering is scaled up.
    SCALE = {"cover": 1.0, "waterfall": 1.5, "scurve": 1.5, "lookahead": 1.3, "rain": 1.35}

    def svg(self, name: str) -> str:
        self._k = self.SCALE.get(name, 1.15)
        return getattr(self, "svg_" + name)()

    def _text(self, x, y, s, size=9, fill=INK, family=MONO, anchor="start", weight=400, style=""):
        extra = f' font-style="{style}"' if style else ""
        size = round(size * getattr(self, "_k", 1.0), 1)
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
                f'text-anchor="{anchor}" font-weight="{weight}"{extra}>{esc(str(s))}</text>')

    def svg_cover(self) -> str:
        c = self.T["cover"]
        t = self._text
        rows = []
        y0, step, x0 = 30, 52, 104

        def lane(i, label):
            y = y0 + i * step
            return y, t(0, y + 15, label, 11, INK3)

        # row 157: a bar that grew from 12 to 20
        y, lab = lane(0, c[0])
        rows.append(lab + f'<rect x="{x0+236}" y="{y}" width="72" height="11" fill="none" stroke="{INK3}" stroke-width="1"/>'
                    f'<rect x="{x0+236}" y="{y+14}" width="120" height="11" fill="{INK}"/>'
                    f'<rect x="{x0+308}" y="{y+14}" width="48" height="11" fill="{REF}"/>'
                    + t(x0 + 368, y + 19, c[1], 15, INK, SERIF, style="italic"))
        # row 29: finished, the end moved back onto the baseline
        y, lab = lane(1, c[2])
        rows.append(lab + f'<rect x="{x0+20}" y="{y}" width="96" height="11" fill="none" stroke="{INK3}" stroke-width="1"/>'
                    f'<rect x="{x0+20}" y="{y+14}" width="84" height="11" fill="{INK}"/>'
                    f'<line x1="{x0+104}" y1="{y-5}" x2="{x0+104}" y2="{y+31}" stroke="{REF}" stroke-width="1.5"/>'
                    f'<path d="M{x0+116} {y+5.5} h-9 m3 -3 l-3 3 l3 3" fill="none" stroke="{REF}" stroke-width="1.2"/>'
                    + t(x0 + 128, y + 19, c[3], 15, INK, SERIF, style="italic"))
        # row 119: there, then gone
        y, lab = lane(2, c[4])
        rows.append(lab + f'<rect x="{x0+150}" y="{y}" width="60" height="11" fill="{INK3}"/>'
                    f'<rect x="{x0+150}" y="{y+14}" width="60" height="11" fill="none" stroke="{REF}" stroke-width="1" stroke-dasharray="3 3"/>'
                    + t(x0 + 222, y + 19, c[5], 15, INK, SERIF, style="italic"))
        # row 57: new
        y, lab = lane(3, c[6])
        rows.append(lab + f'<rect x="{x0+236}" y="{y+14}" width="54" height="11" fill="{REF}"/>'
                    + t(x0 + 302, y + 19, c[7], 15, INK, SERIF, style="italic"))
        # row 63: held by a constraint
        y, lab = lane(4, c[8])
        rows.append(lab + f'<rect x="{x0+196}" y="{y}" width="50" height="11" fill="none" stroke="{INK3}" stroke-width="1"/>'
                    f'<rect x="{x0+268}" y="{y+14}" width="50" height="11" fill="{INK}"/>'
                    f'<path d="M{x0+246} {y+5.5} h18 m-4 -3 l4 3 l-4 3" fill="none" stroke="{REF}" stroke-width="1.2"/>'
                    + t(x0 + 330, y + 19, c[9], 15, INK, SERIF, style="italic"))
        base = y0 + 5 * step + 4
        xa, xb = x0 + 180, x0 + 214
        return (f'<svg viewBox="0 0 688 {base+22}" aria-hidden="true">'
                f'<line x1="{xa}" y1="6" x2="{xa}" y2="{base}" stroke="{INK3}" stroke-width="1" stroke-dasharray="2 4"/>'
                f'<line x1="{xb}" y1="6" x2="{xb}" y2="{base}" stroke="{REF}" stroke-width="1" stroke-dasharray="2 4"/>'
                + t(xa - 4, 12, self.T["rev_a"], 9.5, INK3, anchor="end") + t(xb + 4, 12, self.T["rev_b"], 9.5, REF)
                + "".join(rows)
                + f'<line x1="0" y1="{base}" x2="688" y2="{base}" stroke="{REF}" stroke-width="2"/>'
                + t(0, base + 14, c[10], 9.5, REF) + "</svg>")

    def _road(self, pins: bool) -> str:
        t = self._text
        x0, x1 = 30.0, 666.0
        km = lambda k: x0 + (k - 12) * (x1 - x0) / 24
        top = 96 if pins else 34
        parts = [f'<rect x="{x0}" y="{top}" width="{x1-x0}" height="20" fill="{INK}"/>',
                 f'<line x1="{x0}" y1="{top+10}" x2="{x1}" y2="{top+10}" stroke="#FBF9F4" stroke-width="1.2" stroke-dasharray="9 7"/>']
        for i, k in enumerate((12, 18, 24, 30, 36)):
            x = km(k)
            parts.append(f'<line x1="{x}" y1="{top-6}" x2="{x}" y2="{top+30}" stroke="{INK}" stroke-width="1"/>')
            parts.append(t(x, top + 42, f"km {k}", 9, INK, anchor="middle", weight=600))
            if i < 4:
                parts.append(t(km(k + 3), top + 42, f'{self.T["seg"]} {i+1}', 9, INK3, anchor="middle"))
        xv = km(27.4)
        parts.append(f'<rect x="{xv-13}" y="{top-3}" width="26" height="26" fill="#FBF9F4" stroke="{REF}" stroke-width="1.5"/>'
                     f'<path d="M{xv-13} {top+23} q13 -22 26 0" fill="none" stroke="{REF}" stroke-width="1.5"/>'
                     f'<rect x="{xv-13}" y="{top+5}" width="26" height="6" fill="{REF}"/>')
        parts.append(t(xv, top + 58, self.T["viaduct"], 9, REF, anchor="middle", weight=600))
        height = top + 66
        if pins:
            # item number of examples/README.md, placed where the planted row sits
            spots = [(7, 13.6, 0), (3, 15.6, 0), (6, 19.4, 0), (11, 21.3, 0), (2, 22.9, 0), (8, 25.3, 0),
                     (12, 29.3, 0), (9, 27.0, 1), (13, 27.9, 1), (8, 31.2, 0), (11, 32.6, 0), (10, 34.2, 0)]
            for n, k, level in spots:
                x, y = km(k), 62 - level * 30
                parts.append(f'<line x1="{x}" y1="{y+9}" x2="{x}" y2="{top}" stroke="{REF}" stroke-width="1"/>'
                             f'<circle cx="{x}" cy="{y}" r="9.5" fill="{REF}"/>'
                             + t(x, y + 3.4, n, 9.5, "#fff", anchor="middle", weight=600))
            parts.append(t(x0, 16, self.T["whole"].upper(), 8, INK3))
            for i, n in enumerate((1, 4, 5, 14)):
                x = x0 + 9.5 + i * 24
                parts.append(f'<circle cx="{x}" cy="34" r="9.5" fill="none" stroke="{REF}" stroke-width="1.4"/>'
                             + t(x, 37.4, n, 9.5, REF, anchor="middle", weight=600))
        return f'<svg viewBox="0 0 696 {height}" aria-hidden="true">{"".join(parts)}</svg>'

    def svg_road(self):
        return self._road(False)

    def svg_roadpins(self):
        return self._road(True)

    def svg_milestones(self) -> str:
        t = self._text
        ms = self.j["review-forecast"]["milestone_bands"]["milestones"]
        d0, d1 = dt.date(2027, 1, 1), dt.date(2027, 11, 30)
        xa, xb = 300.0, 686.0
        X = lambda iso: xa + (dt.date.fromisoformat(iso[:10]) - d0).days / (d1 - d0).days * (xb - xa)
        parts = []
        top = 34
        for m in range(1, 12):
            x = X(f"2027-{m:02d}-01")
            parts.append(f'<line x1="{x:.1f}" y1="{top-8}" x2="{x:.1f}" y2="{top + 7*27 - 6}" stroke="{LINE}" stroke-width="1"/>')
            parts.append(t(x + 3, top - 12, self.T["months"][m - 1], 8, INK3))
        h = self.T["ms_head"]
        parts += [t(0, top - 12, h[0].upper(), 7.5, INK3), t(232, top - 12, h[1].upper(), 7.5, INK3, anchor="end"),
                  t(288, top - 12, h[2].upper(), 7.5, INK3, anchor="end")]
        for i, m in enumerate(ms):
            y = top + i * 27 + 8
            late = m["p80_margin_days"] < 0
            parts.append(t(0, y + 3, f'{m["id"]:>2}', 8.5, REF, weight=600))
            parts.append(t(20, y + 3.5, self.T["ms"][m["id"]], 10.5, INK, SERIF, weight=600))
            parts.append(t(232, y + 3, f'{m["margin_days"]:+d} {self.T["days"]}'.replace("-", "−"), 9, INK, anchor="end", weight=600))
            parts.append(t(288, y + 3, f'{m["p80_margin_days"]:+d} {self.T["days"]}'.replace("-", "−"), 9,
                           REF if late else INK3, anchor="end", weight=600 if late else 400))
            xf, xd, xp = X(m["finish"]), X(m["deadline"]), X(m["p80"])
            if late:
                parts.append(f'<rect x="{xd:.1f}" y="{y-5}" width="{xp-xd:.1f}" height="10" fill="{REF}" opacity=".18"/>')
            parts.append(f'<line x1="{xf:.1f}" y1="{y}" x2="{xp:.1f}" y2="{y}" stroke="{INK}" stroke-width="1"/>')
            parts.append(f'<line x1="{xd:.1f}" y1="{y-9}" x2="{xd:.1f}" y2="{y+9}" stroke="{REF}" stroke-width="2"/>')
            parts.append(f'<circle cx="{xp:.1f}" cy="{y}" r="3.6" fill="#fff" stroke="{REF if late else INK}" stroke-width="1.3"/>')
            parts.append(f'<circle cx="{xf:.1f}" cy="{y}" r="3.8" fill="{INK}"/>')
        ly = top + 7 * 27 + 12
        parts += [f'<circle cx="304" cy="{ly-3}" r="3.8" fill="{INK}"/>', t(312, ly, self.T["ms_finish"], 8, INK3),
                  f'<line x1="392" y1="{ly-10}" x2="392" y2="{ly+4}" stroke="{REF}" stroke-width="2"/>', t(398, ly, self.T["ms_deadline"], 8, INK3),
                  f'<circle cx="478" cy="{ly-3}" r="3.6" fill="#fff" stroke="{INK}" stroke-width="1.3"/>', t(486, ly, self.T["ms_p80"], 8, INK3)]
        return f'<svg viewBox="0 0 696 {ly+8}" aria-hidden="true">{"".join(parts)}</svg>'

    def svg_waterfall(self) -> str:
        t = self._text
        c = self.j["cycle"]
        a, b = c["previous"]["percent_earned"], c["current"]["percent_earned"]
        up = c["decomposition_sums_to_points"]
        rm = c["residual_terms"]["removed_earned"]["points"]
        bac = c["residual_terms"]["bac_change"]["points"]
        lo, hi = 23.0, 28.8
        y = lambda v: 150 - (v - lo) / (hi - lo) * 130
        xs = [18, 92, 166, 240, 314]
        w = 52
        lab = self.T["wf"]
        parts = []
        for v in (24, 25, 26, 27, 28):
            parts.append(f'<line x1="14" y1="{y(v):.1f}" x2="372" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
            parts.append(t(376, y(v) + 3, f"{v}%", 7.5, INK3))
        peak = a + up
        mid = peak + rm
        # levels and steps
        parts.append(f'<line x1="{xs[0]}" y1="{y(a):.1f}" x2="{xs[1]}" y2="{y(a):.1f}" stroke="{INK}" stroke-width="2"/>')
        parts.append(f'<rect x="{xs[1]}" y="{y(peak):.1f}" width="{w}" height="{y(a)-y(peak):.1f}" fill="{INK}"/>')
        parts.append(f'<line x1="{xs[1]+w}" y1="{y(peak):.1f}" x2="{xs[2]+w}" y2="{y(peak):.1f}" stroke="{INK3}" stroke-width="1" stroke-dasharray="2 3"/>')
        parts.append(f'<rect x="{xs[2]}" y="{y(peak):.1f}" width="{w}" height="{max(y(mid)-y(peak),1.5):.1f}" fill="{REF}"/>')
        parts.append(f'<line x1="{xs[2]+w}" y1="{y(mid):.1f}" x2="{xs[3]+w}" y2="{y(mid):.1f}" stroke="{INK3}" stroke-width="1" stroke-dasharray="2 3"/>')
        parts.append(f'<rect x="{xs[3]}" y="{y(mid):.1f}" width="{w}" height="{max(y(b)-y(mid),1.5):.1f}" fill="{REF}"/>')
        parts.append(f'<line x1="{xs[3]+w}" y1="{y(b):.1f}" x2="{xs[4]+w}" y2="{y(b):.1f}" stroke="{INK}" stroke-width="2"/>')
        vals = [self.num(a) + "%", self.num(up, sign=True), self.num(rm, sign=True), self.num(bac, sign=True), self.num(b) + "%"]
        ys = [y(a) - 8, y(peak) - 6, y(peak) - 6, y(peak) - 6, y(b) + 21]
        for i in range(5):
            cx = xs[i] + w / 2
            parts.append(t(cx, ys[i], vals[i], 11, REF if i in (2, 3) else INK, SERIF, anchor="middle", weight=600))
            words = lab[i].split(" ")
            half = (len(words) + 1) // 2 if len(words) > 1 else 1
            parts.append(t(cx, 168, " ".join(words[:half]), 7.5, INK3, anchor="middle"))
            if words[half:]:
                parts.append(t(cx, 178, " ".join(words[half:]), 7.5, INK3, anchor="middle"))
        return f'<svg viewBox="0 0 400 184" aria-hidden="true">{"".join(parts)}</svg>'

    def svg_scurve(self) -> str:
        t = self._text
        s = self.j["review-scurve"]
        per = s["periods"]
        n = len(per)
        x = lambda i: 40 + i * (366 - 40) / (n - 1)
        y = lambda v: 150 - v / 100 * 132
        parts = []
        for v in (0, 25, 50, 75, 100):
            parts.append(f'<line x1="40" y1="{y(v):.1f}" x2="368" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
            parts.append(t(36, y(v) + 3, f"{v}%", 7.5, INK3, anchor="end"))
        for i, p in enumerate(per):
            if i % 3 == 0:
                yy, mm = p["period"].split("-")
                parts.append(t(x(i), 164, f'{self.T["months"][int(mm)-1]} {yy[2:]}', 7.5, INK3, anchor="middle"))
        planned = " ".join(f"{x(i):.1f},{y(p['planned_cum_pct']):.1f}" for i, p in enumerate(per))
        earned = [(i, p["earned_cum_pct"]) for i, p in enumerate(per) if p["earned_cum_pct"] is not None]
        earned_pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in earned)
        k = earned[-1][0]
        parts.append(f'<line x1="{x(k):.1f}" y1="14" x2="{x(k):.1f}" y2="150" stroke="{INK3}" stroke-width="1" stroke-dasharray="2 3"/>')
        parts.append(t(x(k) - 4, 22, self.T["status"], 7.5, INK3, anchor="end"))
        parts.append(f'<polyline points="{planned}" fill="none" stroke="{INK}" stroke-width="1.4"/>')
        parts.append(f'<polyline points="{earned_pts}" fill="none" stroke="{REF}" stroke-width="2.4"/>')
        tot = s["totals"]
        parts.append(f'<circle cx="{x(k):.1f}" cy="{y(tot["earned_pct"]):.1f}" r="3.4" fill="{REF}"/>')
        parts.append(t(x(k) - 8, y(tot["planned_pct"]) - 16, f'{self.T["planned"]} {self.num(tot["planned_pct"])}%', 9, INK, SERIF, anchor="end", weight=600))
        parts.append(t(x(k) + 8, y(tot["earned_pct"]) + 14, f'{self.T["earned"]} {self.num(tot["earned_pct"])}%', 9, REF, SERIF, weight=600))
        return f'<svg viewBox="0 0 384 170" aria-hidden="true">{"".join(parts)}</svg>'

    def svg_chain(self) -> str:
        t = self._text
        ms = [m for m in self.j["review-forensics"]["milestones"] if m["id"] == 9][0]
        chain = list(reversed(ms["chain"]))
        n = len(chain)
        x = lambda i: 46 + i * (670 - 46) / (n - 1)
        y = lambda v: 150 - v / 30 * 120
        parts = []
        for v in (0, 10, 20, 30):
            parts.append(f'<line x1="34" y1="{y(v):.1f}" x2="686" y2="{y(v):.1f}" stroke="{GRID if v else INK}" stroke-width="1"/>')
            parts.append(t(28, y(v) + 3, f"+{v}" if v else "0", 7.5, INK3, anchor="end"))
        parts.append(t(34, 18, self.T["chain_y"].upper(), 7.5, INK3))
        pts = []
        for i, c in enumerate(chain):
            if i:
                pts.append(f"{x(i):.1f},{y(chain[i-1]['variance_days']):.1f}")
            pts.append(f"{x(i):.1f},{y(c['variance_days']):.1f}")
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{REF}" stroke-width="2"/>')
        prev = None
        for i, c in enumerate(chain):
            v = c["variance_days"]
            jump = prev is None or v != prev
            fill = INK if c["started"] else "#fff"
            parts.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4.2" fill="{fill}" stroke="{INK}" stroke-width="1.4"/>')
            parts.append(t(x(i), 166, c["id"], 9, REF if jump else INK, anchor="middle", weight=600 if jump else 400))
            if jump:
                parts.append(t(x(i) - 6 if i else x(i), y(v) - 10, f"+{v}", 12, INK, SERIF, anchor="end" if i else "middle", weight=600))
            prev = v
        parts.append(t(x(0) + 9, y(chain[0]["variance_days"]) + 16, self.T["chain_origin"], 10, INK, SERIF, style="italic"))
        k = [i for i, c in enumerate(chain) if c["id"] == 157][0]
        parts.append(t(x(k) + 8, y(chain[k]["variance_days"]) + 16, self.T["chain_amp"], 10, INK, SERIF, style="italic"))
        parts.append(t(x(n - 1), 178, self.T["chain_ms"], 7.5, INK3, anchor="middle"))
        parts += [f'<circle cx="440" cy="15" r="4.2" fill="{INK}" stroke="{INK}" stroke-width="1.4"/>', t(450, 18, self.T["chain_started"], 8, INK3),
                  f'<circle cx="530" cy="15" r="4.2" fill="#fff" stroke="{INK}" stroke-width="1.4"/>', t(540, 18, self.T["chain_not"], 8, INK3)]
        return f'<svg viewBox="0 0 696 184" aria-hidden="true">{"".join(parts)}</svg>'

    def svg_lookahead(self) -> str:
        t = self._text
        la = self.j["review-forecast"]["lookahead"][0]
        a, b = la["planned_earning_pct"], la["projected_pct"]
        w = lambda v: v / 12 * 250
        lab = self.T["look"]
        return (f'<svg viewBox="0 0 330 86" aria-hidden="true">'
                + t(0, 11, lab[0], 8.5, INK3)
                + f'<rect x="0" y="17" width="{w(a):.1f}" height="16" fill="none" stroke="{INK}" stroke-width="1.4"/>'
                + t(w(a) + 8, 30, self.num(a) + "%", 13, INK, SERIF, weight=600)
                + t(0, 55, lab[1], 8.5, INK3)
                + f'<rect x="0" y="61" width="{w(b):.1f}" height="16" fill="{REF}"/>'
                + t(w(b) + 8, 74, self.num(b) + "%", 13, REF, SERIF, weight=600) + "</svg>")

    def svg_rain(self) -> str:
        t = self._text
        r = self.j["review-forecast"]["rain_exposure"]
        months = r["months"]
        top = max(m["remaining"] for m in months)
        n = len(months)
        bw = 20
        x = lambda i: 4 + i * (330 - 8) / n
        parts = [f'<line x1="0" y1="96" x2="330" y2="96" stroke="{INK}" stroke-width="1"/>']
        for i, m in enumerate(months):
            h = m["remaining"] / top * 80
            res = m["in_reserve"] > 0
            parts.append(f'<rect x="{x(i):.1f}" y="{96-h:.1f}" width="{bw}" height="{h:.1f}" '
                         + (f'fill="{REF}"/>' if res else f'fill="#fff" stroke="{INK}" stroke-width="1"/>'))
            mm = int(m["period"].split("-")[1])
            parts.append(t(x(i) + bw / 2, 107, self.T["months"][mm - 1], 7, REF if res else INK3, anchor="middle"))
        parts += [f'<rect x="0" y="116" width="9" height="9" fill="{REF}"/>', t(14, 124, self.T["rain_res"], 8, INK3)]
        return f'<svg viewBox="0 0 330 128" aria-hidden="true">{"".join(parts)}</svg>'

    # -- blocks built from the JSON ------------------------------------------
    def html(self, name: str) -> str:
        return getattr(self, "html_" + name)()

    def html_quality(self) -> str:
        T = self.T
        out = []
        for m in self.j["review-quality"]["metrics"]:
            st = m["status"]
            if m["code"] in ("Q13", "Q14"):
                value = self.num(m["share_pct"] / 100, 3 if m["code"] == "Q13" else 2)
                sub = T["q_min"].format(t=self.num(m["threshold_pct"] / 100, 2))
            elif m["code"] == "Q12":
                value, sub = ("n/c" if self.lang == "pt" else "n/a"), ""
            else:
                value = T["q_of"].format(a=m["count"], b=m["population"])
                sub = self.num(m["share_pct"], 2) + "%"
                if m["threshold_pct"] is not None:
                    sub += " · " + T["q_lim"].format(t=self.num(m["threshold_pct"], 0))
            label = {"pass": T["q_pass"], "fail": T["q_fail"]}.get(st) or (T["q_nc"] if m["code"] == "Q12" else T["q_none"])
            out.append(f'<div class="{st or "na"}"><div class="c">{m["code"]}</div><div class="t">{esc(m["title"])}</div>'
                       f'<div class="v">{value}</div><div class="s">{sub}</div><div class="st">{label}</div></div>')
        return '<div class="q">' + "".join(out) + "</div>"

    def html_demands(self) -> str:
        out, group = [], None
        for d in self.j["cycle-readings"]["demands"]:
            if d["group"] != group:
                if group is not None:
                    out.append("</ol>")
                group = d["group"]
                out.append(f"<h3>{esc(group)}</h3><ol>")
                k = 0
            k += 1
            out.append(f'<li><span>{k}</span><div>{esc(d["text"])}</div></li>')
        out.append("</ol>")
        return '<div class="dem">' + "".join(out) + "</div>"

    def _ba(self, row, name, planted, field, before, after, why, gone=False, prev=False):
        T = self.T
        rowlab = f'{T["row"]} {row}'
        return (f'<div class="ba"><div class="hd"><span class="row">{rowlab}</span><span class="nm">{esc(name)}</span>'
                f'<span class="planted">{T["planted"].format(n=planted)}</span></div>'
                f'<div class="two"><div class="side"><div class="rv">rev03</div><div class="f">{field}</div><div class="v">{before}</div></div>'
                f'<div class="arrow">→</div>'
                f'<div class="side after"><div class="rv">rev04</div><div class="f">{field}</div><div class="v{" gone" if gone else ""}">{after}</div></div></div>'
                f'<div class="why"><b class="mark eng">{T["eng"]}</b>{why}</div></div>')

    def html_ba29(self):
        B = self.T["ba"]
        p = self.j["cycle"]["past_rewritten"]["actual_finish"][0]
        return self._ba(29, p["name"], 7, B["f_actual"], self.date(p["before"]), self.date(p["after"]), self.reading("cycle", "c5", 2))

    def html_ba119(self):
        B = self.T["ba"]
        p = self.j["cycle"]["past_rewritten"]["removed_with_progress"][0]
        return self._ba(119, p["name"], 11, B["f_state"], B["pct"].format(p=int(p["percent"])), B["gone"],
                        self.reading("cycle", "c5", 1), gone=True)

    def html_ba132(self):
        B = self.T["ba"]
        p = self.j["cycle"]["baseline_moved"][0]
        return self._ba(132, p["name"], 10, B["f_bl"], B["kept"], B["moved"].format(d=int(p["baseline_finish_moved_days"])),
                        self.reading("review", "forensics", 1))

    def html_ba157(self):
        B = self.T["ba"]
        p = self.j["cycle"]["duration_changed"][0]
        return self._ba(157, p["name"], 9, B["f_dur"], B["wd"].format(n=int(p["duration_before_days"])),
                        B["wd"].format(n=int(p["duration_after_days"])), self.reading("cycle", "c4", 0))

    def html_ba63(self):
        B = self.T["ba"]
        p = self.j["cycle"]["critical_path"]["float_fell_top"][0]
        assert p["id"] == 63
        return self._ba(63, p["name"], 2, B["f_finish"], self.date(p["finish_before"]), self.date(p["finish_after"]),
                        self.demand(4) + " " + self.demand(10))

    def html_ba57(self):
        B = self.T["ba"]
        p = self.j["cycle"]["unmatched"]["inserted"][0]
        return self._ba(57, p["name"], 11, B["f_budget"], B["absent"], self.money(p["baseline_cost"]), self.demand(8))

    def html_balinks(self):
        B = self.T["ba"]
        lg = self.j["cycle"]["logic"]
        a, r = lg["links_added"][0], lg["links_removed"][0]
        T = self.T
        one = (f'<div class="ba"><div class="hd"><span class="row">{T["row"]} {r["id"]}</span><span class="nm">{esc(r["name"])}</span>'
               f'<span class="planted">{T["planted"].format(n=8)}</span></div>'
               f'<div class="two"><div class="side"><div class="rv">rev03</div><div class="f">{B["f_link"]}</div><div class="v">{r["predecessor_id"]} → {r["id"]}</div></div>'
               f'<div class="arrow">→</div><div class="side after"><div class="rv">rev04</div><div class="f">{B["f_link"]}</div><div class="v gone">{B["removed"]}</div></div></div>'
               f'<div class="why"><b class="mark eng">{T["eng"]}</b>{self.demand(9)}</div></div>')
        two = (f'<div class="ba"><div class="hd"><span class="row">{T["row"]} {a["id"]}</span><span class="nm">{esc(a["name"])}</span>'
               f'<span class="planted">{T["planted"].format(n=8)}</span></div>'
               f'<div class="two"><div class="side"><div class="rv">rev03</div><div class="f">{B["f_link"]}</div><div class="v">{B["none"]}</div></div>'
               f'<div class="arrow">→</div><div class="side after"><div class="rv">rev04</div><div class="f">{B["f_link"]}</div><div class="v">{a["predecessor_id"]} → {a["id"]}</div></div></div>'
               f'<div class="why"><b class="mark eng">{T["eng"]}</b>{self.demand(11)}</div></div>')
        return one + two

    def html_chainlist(self):
        ms = [m for m in self.j["review-forensics"]["milestones"] if m["id"] == 9][0]
        rows = "".join(f'<tr><td class="n">{c["id"]}</td><td>{esc(c["name"])}</td>'
                       f'<td class="pg">{self.date(c["finish"])}</td><td class="pg">+{c["variance_days"]}</td></tr>'
                       for c in reversed(ms["chain"]))
        return rows

    # -- assembly -------------------------------------------------------------
    def build(self) -> str:
        src = open(os.path.join(HERE, f"content-{self.lang}.html"), encoding="utf-8").read()
        # Page numbers and the contents list come from the sections themselves.
        sections = re.findall(r'<section class="page[^"]*"([^>]*)>', src)
        toc = []
        for n, attrs in enumerate(sections, 1):
            m = re.search(r'id="([^"]+)"', attrs)
            if m:
                self.pages[m.group(1)] = n
            m = re.search(r'data-toc="([^"]+)"', attrs)
            if m:
                toc.append((m.group(1), n))
        toc_html = '<ol class="toc">' + "".join(f"<li>{t}<span>{n:02d}</span></li>" for t, n in toc) + "</ol>"
        foot = (f'<div class="foot"><span>{esc(self.T["running"].format(v=VERSION))}</span><span class="n"></span></div>')

        def sub(m):
            parts = m.group(1).split()
            kind, args = parts[0], parts[1:]
            if kind == "R":
                return self.reading(*args)
            if kind == "C":
                return self.reading(*args, coded=True)
            if kind == "D":
                return self.demand(args[0])
            if kind == "DC":
                return self.demand(args[0], coded=True)
            if kind == "term":
                return self.term(args[0])
            if kind == "svg":
                return self.svg(args[0])
            if kind == "html":
                return self.html(args[0])
            if kind == "img":
                return self.img(*args)
            if kind == "pg":
                return str(self.pages[args[0]])
            if kind == "name":
                return esc(self.name(int(args[0])))
            if kind == "toc":
                return toc_html
            if kind == "V":
                return VERSION
            if kind == "run":
                return self.run
            if kind == "foot":
                return foot
            if kind == "mark":
                return f'<b class="mark {args[0]}">{self.T[args[0]]}</b>'
            raise KeyError(m.group(0))

        src = src.replace("{{run}}", self.run).replace("{{V}}", VERSION)

        # A sheet may ask for its content to be set slightly larger or smaller (data-z).
        def sheet(m):
            head, inner = m.group(1), m.group(2)
            z = re.search(r'data-z="([\d.]+)"', head)
            style = f' style="zoom:{z.group(1)}"' if z else ""
            tail = "" if "cover" in head else foot
            return f'{head}<div class="in"{style}>{inner}</div>{tail}</section>'

        src = re.sub(r'(<section class="page[^>]*>)(.*?)</section>', sheet, src, flags=re.S)
        body = re.sub(r"\{\{([^}]+)\}\}", sub, src)
        title = "cronoaudit · guia ilustrado" if self.lang == "pt" else "cronoaudit · illustrated guide"
        return (f'<!doctype html>\n<html lang="{"pt-BR" if self.lang == "pt" else "en"}"><head><meta charset="utf-8">\n'
                f"<title>{title} {VERSION}</title>\n"
                '<meta name="author" content="Helton da Silva de Oliveira">\n'
                '<link rel="stylesheet" href="style.css">\n</head><body>\n' + body + "\n</body></html>\n")


def main():
    html_only = "--html-only" in sys.argv
    failed = False
    for lang in ("pt", "en"):
        if not os.path.exists(os.path.join(HERE, f"content-{lang}.html")):
            print(f"skip {lang}: no content-{lang}.html")
            continue
        out = os.path.join(HERE, f"guia-{lang}.html")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(Guide(lang).build())
        print(out)
        if not html_only:
            pdf = os.path.join(HERE, f"guia-{lang}.pdf")
            done = subprocess.run(["node", os.path.join(HERE, "topdf.js"), out, pdf])
            if done.returncode:
                failed = True
    if failed:
        sys.exit("the PDF check failed: see the CHECK lines above")


if __name__ == "__main__":
    main()
