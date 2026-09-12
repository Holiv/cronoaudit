#!/usr/bin/env python3
"""Render a review or a cycle comparison as one self-contained HTML file.

No external requests of any kind: no CDN, no web font, no image host. Everything
is inline, so the file opens from a network share, from an email attachment, or
from a laptop with no connection, and it still looks the same in five years.

It prints to PDF from the browser with one button, because the artefact that ends
up attached to a meeting record is a PDF, and a report that cannot become one gets
screenshotted instead.
"""
from __future__ import annotations

import html
import json
from datetime import datetime

LABELS = {
    "A1": "Successor started without the predecessor complete",
    "A2": "Total inversion: successor complete, predecessor not started",
    "H": "Trend date elapsed with no actual progress",
    "E": "Pulled forward beyond threshold and never started",
    "C": "Delayed beyond threshold",
    "G": "Duration disagrees with the start-to-finish window",
    "B": "Milestone with no deadline set",
    "F": "In progress with percent complete at zero",
    "P": "Pending record: declared complete with no actual finish",
}
LAYER = {
    "A1": "Network integrity", "A2": "Network integrity",
    "H": "Date adherence", "E": "Date adherence", "C": "Date adherence",
    "G": "Reporting consistency", "B": "Reporting consistency",
    "F": "Reporting consistency", "P": "Reporting consistency",
}
HOW = {
    "A1": "Filter activities with an actual start whose predecessor has no actual finish. "
          "Both ends of each violated link are listed.",
    "A2": "Filter activities with an actual finish whose predecessor has no actual start.",
    "H": "Compare the finish date against the status date, keeping only activities with "
         "neither an actual start nor an actual finish.",
    "E": "Finish minus baseline finish, at or below minus the threshold, with no actual start.",
    "C": "Finish minus baseline finish, at or above the threshold.",
    "G": "Duration converted to days against the file's minutes-per-day, compared with the "
         "working days between start and finish.",
    "B": "Filter milestones with no deadline field set.",
    "F": "Filter activities with an actual start, no actual finish, and percent complete at zero.",
    "P": "Filter activities at 100 percent with no actual finish.",
}
ORDER = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]

CSS = """
:root{
  --bg:#fbfaf8; --panel:#fff; --ink:#1a1a1a; --muted:#5b5b5b; --line:#e4e1dc;
  --accent:#1f4e5f; --warn:#8a4b1e; --warnbg:#fdf4ec; --ok:#2f6b4f;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#15161a; --panel:#1d1f24; --ink:#ecebe8; --muted:#a2a2a0; --line:#31343b;
    --accent:#7fb3c4; --warn:#e0a26a; --warnbg:#2a2119; --ok:#7fc0a0;
  }
}
:root[data-theme="dark"]{
  --bg:#15161a; --panel:#1d1f24; --ink:#ecebe8; --muted:#a2a2a0; --line:#31343b;
  --accent:#7fb3c4; --warn:#e0a26a; --warnbg:#2a2119; --ok:#7fc0a0;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
.wrap{max-width:1060px;margin:0 auto;padding-block:28px;padding-left:20px;padding-right:20px}
h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:1.05rem;margin:32px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:.95rem;margin:20px 0 6px}
.sub{color:var(--muted);font-size:.85rem;margin:0 0 20px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:22px}
button{font:inherit;padding:7px 13px;border:1px solid var(--line);border-radius:7px;
  background:var(--panel);color:var(--ink);cursor:pointer}
button:hover{border-color:var(--accent)}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:8px}
.meta div{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.meta dt{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.meta dd{margin:3px 0 0;font-family:var(--mono);font-size:.9rem;word-break:break-word}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:12px 13px}
.card .code{font-family:var(--mono);font-weight:700;color:var(--accent);font-size:.85rem}
.card .n{font-size:1.85rem;font-weight:650;line-height:1.1;margin:2px 0}
.card .n.zero{color:var(--muted);font-weight:500}
.card .lab{font-size:.79rem;color:var(--muted)}
.card .layer{font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-top:6px}
.note{background:var(--warnbg);border:1px solid var(--warn);border-left-width:4px;
  border-radius:7px;padding:11px 14px;margin:10px 0;font-size:.89rem}
.note.good{background:transparent;border-color:var(--ok);color:var(--ink)}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:9px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:.84rem}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
  position:sticky;top:0;background:var(--panel)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-family:var(--mono)}
td.name{white-space:normal;min-width:220px}
.pos{color:var(--ok)} .neg{color:var(--warn)}
.how{font-size:.82rem;color:var(--muted);margin:6px 0 10px}
.how b{color:var(--ink);font-weight:600}
details{margin:8px 0}
summary{cursor:pointer;font-size:.88rem;color:var(--accent)}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);
  font-size:.78rem;color:var(--muted)}
@media print{
  :root{--bg:#fff;--panel:#fff;--ink:#000;--muted:#444;--line:#bbb}
  .bar{display:none} body{font-size:10.5pt} th{position:static}
  h2{break-after:avoid} .scroll{overflow:visible;border-color:#bbb}
  table{font-size:8.5pt} td,th{white-space:normal}
}
"""

JS = """
document.getElementById('pdf').addEventListener('click',()=>window.print());
document.getElementById('theme').addEventListener('click',()=>{
  const r=document.documentElement;
  const dark=getComputedStyle(r).getPropertyValue('--bg').trim().startsWith('#15');
  r.setAttribute('data-theme',dark?'light':'dark');
});
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def num(v, digits=1):
    if v is None:
        return "&mdash;"
    if isinstance(v, float):
        return f"{v:,.{digits}f}"
    return f"{v:,}"


def table(headers, rows):
    if not rows:
        return '<p class="how">No activities in this finding.</p>'
    th = "".join(f"<th>{esc(h)}</th>" for h, _ in headers)
    body = []
    for r in rows:
        tds = []
        for h, key in headers:
            v = r.get(key)
            cls = "num" if isinstance(v, (int, float)) and not isinstance(v, bool) else ""
            if key == "name":
                cls = "name"
            tds.append(f'<td class="{cls}">{esc(v) if not isinstance(v,float) else num(v)}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    return (
        '<div class="scroll"><table><thead><tr>' + th + "</tr></thead><tbody>"
        + "".join(body) + "</tbody></table></div>"
    )


def shell(title, subtitle, body):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>{esc(title)}</h1>
<p class="sub">{subtitle}</p>
<div class="bar">
  <button id="pdf">Print / save as PDF</button>
  <button id="theme">Toggle theme</button>
</div>
{body}
<footer>
Generated by the <b>schedule-integrity</b> skill from the schedule's own XML export.
Every finding above states the filter that reproduces it, so any number here can be
checked in the source file without trusting this report.
</footer>
</div><script>{JS}</script></body></html>
"""


def render_review(res: dict) -> str:
    conv = res["conventions"]
    counts = res["counts"]
    total = sum(c["distinct_activities"] for c in counts.values())

    meta = "".join(
        f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>"
        for k, v in [
            ("Source file", res.get("source")),
            ("Baseline slot used", conv.get("baseline_slot")),
            ("Threshold", f"{conv['threshold_days']} calendar days"),
            ("Population", conv.get("population")),
            ("Percent source", conv.get("percent_source")),
            ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]
    )
    out = [f'<div class="meta">{meta}</div>']

    for b in res.get("blocking", []):
        out.append(f'<div class="note"><b>Blocking.</b> {esc(b)}</div>')

    net = counts["A1"]["distinct_activities"] + counts["A2"]["distinct_activities"]
    if net:
        out.append(
            f'<div class="note"><b>Read this before any date below.</b> {net} activities are '
            "involved in violated logic. When the scheduling tool recalculates over a network "
            "the works does not follow, every forecast date in this file is derived from a "
            "false premise. Settle the network findings before discussing a single date.</div>"
        )
    else:
        out.append(
            '<div class="note good"><b>Network integrity holds.</b> No out-of-sequence '
            "execution found, so the forecast dates below rest on logic the works is "
            "actually following.</div>"
        )

    out.append("<h2>Findings</h2>")
    cards = []
    for code in ORDER:
        c = counts[code]
        n = c["distinct_activities"]
        cards.append(
            f'<div class="card"><div class="code">{code}</div>'
            f'<div class="n{" zero" if not n else ""}">{n}</div>'
            f'<div class="lab">{esc(LABELS[code])}</div>'
            f'<div class="layer">{esc(LAYER[code])}</div></div>'
        )
    out.append('<div class="cards">' + "".join(cards) + "</div>")

    out.append(
        f'<p class="how" style="margin-top:14px"><b>Counting convention.</b> '
        f'{esc(conv["network_counting"])} '
        "Each card shows distinct activities; the tables show one row per marked role, so a "
        "row count can legitimately exceed the card.</p>"
    )

    for code in ORDER:
        items = res["findings"][code]
        c = counts[code]
        out.append(f"<h2>{code} &mdash; {esc(LABELS[code])}</h2>")
        extra = ""
        if code in ("A1", "A2"):
            extra = (
                f" Counted three defensible ways: {c['distinct_activities']} distinct "
                f"activities, {c['as_successors']} as successors, "
                f"{c['as_predecessors']} as predecessors."
            )
        out.append(
            f'<p class="how"><b>How to reproduce.</b> {esc(HOW[code])}{esc(extra)}</p>'
        )
        if code == "G":
            out.append(
                '<div class="note"><b>Thermometer, not a finding.</b> G says something was '
                "edited inconsistently; it does not say what. Use it to choose what to "
                "inspect, and do not report it on its own.</div>"
            )
        if code == "P" and items:
            out.append(
                '<div class="note"><b>This is a record defect, not an execution defect.</b> '
                "These activities are excluded from the network findings above. Without that "
                "rule a reporting problem gets reported as an execution problem, and the "
                "conversation with the people doing the work starts by accusing the wrong "
                "thing.</div>"
            )
        headers = [("Code", "code"), ("Row", "id"), ("UID", "uid"), ("Activity", "name")]
        keys = {k for i in items for k in i}
        for h, k in [
            ("Role", "role"), ("Counterpart", "counterpart_name"), ("Link", "link_type"),
            ("Finish", "finish"), ("Days elapsed", "days_elapsed"),
            ("Var. cal. days", "finish_variance_calendar_days"),
            ("Var. work days", "finish_variance_working_days"),
            ("Duration d", "duration_days"), ("Window wd", "window_working_days"),
            ("Actual start", "actual_start"), ("%", "percent"),
        ]:
            if k in keys:
                headers.append((h, k))
        out.append(table(headers, items))

    return shell(
        "Schedule integrity review",
        f"{total} activities across 9 checks &middot; source <code>{esc(res.get('source'))}</code>",
        "\n".join(out),
    )


def render_comparison(r: dict) -> str:
    prev, curr = r["previous"], r["current"]
    meta = "".join(
        f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>"
        for k, v in [
            ("Previous snapshot", prev.get("source")),
            ("Previous status date", prev.get("status_date")),
            ("Current snapshot", curr.get("source")),
            ("Current status date", curr.get("status_date")),
            ("Baseline slot", curr.get("baseline_slot")),
            ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]
    )
    out = [f'<div class="meta">{meta}</div>']

    ex = sum(1 for t in r["trend"] if t["reading"] == "execution")
    rp = sum(1 for t in r["trend"] if t["reading"] == "replan")
    bl = len(r["baseline_moved"])
    cards = [
        ("Earned, previous", num(prev.get("percent_earned"), 2) + "%", "of budget"),
        ("Earned, current", num(curr.get("percent_earned"), 2) + "%", "of budget"),
        ("Movement", num(r.get("movement_points"), 4) + " pp", "headline figure"),
        ("Explained by progress", num(r.get("decomposition_sums_to_points"), 4) + " pp",
         "sum of activity contributions"),
        ("Unexplained residue", num(r.get("movement_unexplained_points"), 4) + " pp",
         "not work done"),
    ]
    out.append(
        '<div class="cards">'
        + "".join(
            f'<div class="card"><div class="code">{esc(a)}</div>'
            f'<div class="n">{b}</div><div class="lab">{esc(c)}</div></div>'
            for a, b, c in cards
        )
        + "</div>"
    )

    out.append("<h2>Was it execution, or was it the plan?</h2>")
    out.append(
        '<p class="how">Three signals, read together. This is the distinction that gives the '
        "comparison meaning: a forecast rewritten with no execution behind it is legitimate, "
        "but it must be visible as a plan change, or next cycle starts from a baseline nobody "
        "agreed to.</p>"
    )
    out.append(
        '<div class="cards">'
        f'<div class="card"><div class="code">EXECUTION</div><div class="n">{ex}</div>'
        '<div class="lab">dates moved with actual dates behind them</div></div>'
        f'<div class="card"><div class="code">REPLAN</div><div class="n">{rp}</div>'
        '<div class="lab">dates moved with no actuals</div></div>'
        f'<div class="card"><div class="code">REFERENCE</div><div class="n">{bl}</div>'
        '<div class="lab">the baseline itself moved</div></div>'
        "</div>"
    )

    for w in r.get("warnings", []):
        out.append(f'<div class="note"><b>Warning.</b> {esc(w)}</div>')

    if r["baseline_moved"]:
        out.append("<h2>The baseline moved &mdash; a finding about the report</h2>")
        out.append(
            '<p class="how">Every deviation figure straddling these changes is measured '
            "against two different references. Two numbers can each be perfectly measured and "
            "their difference still be entirely false.</p>"
        )
        out.append(table(
            [("Row", "id"), ("UID", "uid"), ("Activity", "name"),
             ("Baseline start moved", "baseline_start_moved_days"),
             ("Baseline finish moved", "baseline_finish_moved_days")],
            r["baseline_moved"],
        ))

    out.append("<h2>Where the movement came from</h2>")
    out.append(
        '<p class="how"><b>The weight distribution, not just the aggregate.</b> Contributions '
        "are weight-relative and sum to the movement, so a healthy-looking aggregate can be "
        "read here as the average of two pathologies. Denominator: "
        f"{esc(r['conventions']['denominator'])}.</p>"
    )
    out.append(table(
        [("Row", "id"), ("Activity", "name"), ("WBS", "wbs"),
         ("% previous", "percent_previous"), ("% current", "percent_current"),
         ("Baseline cost", "baseline_cost"), ("Contribution pp", "contribution_points")],
        r["decomposition"][:200],
    ))

    out.append("<h2>Dates that moved</h2>")
    out.append(table(
        [("Row", "id"), ("Activity", "name"), ("Matched by", "matched_by"),
         ("Start moved", "start_moved_days"), ("Finish moved", "finish_moved_days"),
         ("Actuals", "actuals_present"), ("Reading", "reading")],
        r["trend"][:200],
    ))

    ins, rem = r["unmatched"]["inserted"], r["unmatched"]["removed"]
    out.append("<h2>Scope changes</h2>")
    out.append(
        '<p class="how">Two classes only. A renamed activity that also moved branch is '
        "indistinguishable from a removal plus an insertion, so these counts are numbers to "
        "judge rather than a classification to trust.</p>"
    )
    out.append(f"<h3>Inserted ({len(ins)})</h3>")
    out.append(table([("Row", "id"), ("UID", "uid"), ("Activity", "name")], ins))
    out.append(f"<h3>Removed ({len(rem)})</h3>")
    out.append(table([("Row", "id"), ("UID", "uid"), ("Activity", "name")], rem))

    return shell(
        "Cycle comparison",
        f"movement {num(r.get('movement_points'),4)} pp &middot; "
        f"{num(r.get('movement_unexplained_points'),4)} pp unexplained by progress",
        "\n".join(out),
    )


def write(payload: dict, path: str, kind: str) -> str:
    body = render_review(payload) if kind == "review" else render_comparison(payload)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Render a findings or comparison JSON as HTML")
    ap.add_argument("json_file")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--kind", choices=["review", "comparison"], default="review")
    a = ap.parse_args()
    with open(a.json_file, encoding="utf-8") as fh:
        write(json.load(fh), a.out, a.kind)
    print(a.out)
