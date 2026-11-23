#!/usr/bin/env python3
"""Contract tests for the checks. Run: python3 scripts/test_checks.py

Two halves, and the second is the one people skip:

  1. On the positive fixture every check MUST fire.
  2. On the negative fixture every check MUST stay silent.

Without the second half a clean result means nothing -- a probe that cannot fire
reports no findings on a broken file just as happily as on a sound one. Prove the
instrument can pass before trusting a negative.

The third test is the transversal rule, which is the finest judgement in the
method and the easiest to regress.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CODES = ["A1", "A2", "H", "E", "C", "G", "B", "F", "P"]


def analyse(xml_name):
    xml = os.path.join(ROOT, "fixtures", xml_name)
    with tempfile.TemporaryDirectory() as tmp:
        model = os.path.join(tmp, "model.json")
        out = os.path.join(tmp, "findings.json")
        subprocess.run(
            [sys.executable, os.path.join(HERE, "parse_mspdi.py"), xml, "-o", model],
            check=True, capture_output=True,
        )
        subprocess.run(
            [sys.executable, os.path.join(HERE, "run_checks.py"), model, "--json", out],
            check=True, capture_output=True,
        )
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)


def analyse_raw(model):
    """Run the checks in-process, for assertions that need the parsed model too."""
    import run_checks
    return run_checks.run(model, run_checks.DEFAULT_THRESHOLD_DAYS,
                          run_checks.DEFAULT_TOLERANCE_DAYS)


def compare_cycle():
    import compare_snapshots
    import parse_mspdi
    prev = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_prev.xml"))
    curr = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    return compare_snapshots.compare(prev, curr)


REVIEW_SECTIONS = [
    "How to read these numbers", "Index", "Progress by", "Starts per month",
    "S-curve from the file", "<polyline", "Productivity and trend by resource",
    "Network quality", "Baseline execution index", "Looking forward", "Earned Schedule",
    "Forensics of the scenario", "Driving path per milestone", "Reading", "Executive synthesis",
    "Finish variance against baseline", "Total float", "Problem",
    "To reproduce in the scheduling tool", "Conventions this report used",
]
PT_SECTIONS = [
    "Como ler estes n\u00fameros", "\u00cdndice", "Avan\u00e7o por", "Partidas por m\u00eas",
    "Problema", "Para reproduzir no Project", "Conven\u00e7\u00f5es que este relat\u00f3rio usou",
    "Calend\u00e1rios que carregam o trabalho", "Term\u00f4metro",
]
CYCLE_SECTIONS = [
    "Was it execution, or was it the plan", "RESIDUE", "the baseline itself moved",
    "Where the movement came from", "Scope changes",
    "Project finish", "Critical path", "Logic changed", "Duration changed before any start",
    "Past rewritten", "Network quality, before and after", "To reproduce in the scheduling tool",
    "Reading", "cycle_prev.xml", "Cycle fixture curr",
]
CYCLE_PT_SECTIONS = [
    "T\u00e9rmino do projeto", "Caminho cr\u00edtico", "L\u00f3gica alterada",
    "Dura\u00e7\u00e3o alterada", "Passado reescrito", "Qualidade da rede, antes",
    "Para reproduzir no Project", "Leitura", "Linha de base 1",
    "02/10/2026", "16/10/2026", "N\u00e3o Iniciar Antes De 10/08/2026", "TI + 5 d",
]
# What a person must never read, in either report: a local path, a raw timestamp,
# a negative zero, the slot jargon. In Portuguese, no ISO date at all.
FORBID = ["--forbid=/Users/|[A-Za-z]:\\\\|/home/|/tmp/|/var/folders",
          "--forbid=\\d{4}-\\d{2}-\\d{2}T\\d{2}", "--forbid=(^|[^\\d.,])-0([.,]0+)?(?![\\d.,])"]
FORBID = FORBID + [
    "--forbid=\\d[.,]\\d{3,}\\s?%",
    "--forbid=(^|[^\\d.,])1 (atividades|activities|dias|days|grupos|groups|marcos|milestones|v\u00ednculos|links|folhas|leaves)\\b",
]
FORBID_PT = FORBID + ["--forbid=\\d{4}-\\d{2}-\\d{2}", "--forbid=[Gg]aveta"]
# Raw engine keys and English method sentences in a Portuguese report, and a year
# written as a thousand ("2.026"), all seen on a real run (0.7.2).
FORBID_PT_REVIEW = FORBID_PT + [
    "--forbid=predecessor_id|float_days|baseline_finish|lag_days",
    "--forbid=mechanism reconstruction|aggregate and cost-weighted|non-working exceptions on the|"
    "inferred: remaining|outside the chain",
    "--forbid=(^|\\s)2\\.0[2-3]\\d(?=\\s)",
]
BARE_SECTIONS = ["There is no network to hold", "Planned-to-date is unavailable", "unavailable",
                 "carries no earned value of its own", "absence of data",
                 "--forbid=Network integrity holds", "--forbid=In reserve months now"]


def render_checks() -> dict:
    """Generate both reports and execute their own renderer."""
    import shutil

    node = shutil.which("node")
    if node is None:
        return {"failures": [], "skipped": True}

    out = {"failures": [], "skipped": False}
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, os.path.join(HERE, "review.py"),
             os.path.join(ROOT, "fixtures", "cycle_prev.xml"),
             os.path.join(ROOT, "fixtures", "cycle_curr.xml"),
             "--outdir", tmp, "--quiet"],
            check=True, capture_output=True,
        )
        pairs = [
            ("cycle_curr-review.html", REVIEW_SECTIONS + ["Checked, nothing found:"] + FORBID),
            ("cycle_prev--to--cycle_curr-cycle.html", CYCLE_SECTIONS + FORBID),
        ]
        # And again in Portuguese, so a missing label is a failing test rather than
        # an English heading appearing in the middle of a Portuguese report.
        pt_dir = os.path.join(tmp, "pt")
        subprocess.run(
            [sys.executable, os.path.join(HERE, "review.py"),
             os.path.join(ROOT, "fixtures", "cycle_curr.xml"),
             "--outdir", pt_dir, "--quiet", "--lang", "pt"],
            check=True, capture_output=True,
        )
        pairs.append((os.path.join("pt", "cycle_curr-review.html"),
                      PT_SECTIONS + ["Verificados sem ocorr\u00eancia:", "agregado e ponderado por custo"]
                      + FORBID_PT_REVIEW))
        # The cycle pair in Portuguese, and the positive fixture too: it is the one
        # that fills every table of the review, so a raw date has nowhere to hide.
        subprocess.run(
            [sys.executable, os.path.join(HERE, "review.py"),
             os.path.join(ROOT, "fixtures", "cycle_prev.xml"),
             os.path.join(ROOT, "fixtures", "cycle_curr.xml"),
             "--outdir", os.path.join(tmp, "ptc"), "--quiet", "--lang", "pt"],
            check=True, capture_output=True,
        )
        pairs.append((os.path.join("ptc", "cycle_prev--to--cycle_curr-cycle.html"),
                      CYCLE_PT_SECTIONS + FORBID_PT))
        # The review of the current file from a pair run: the only page that shows
        # the cycle forensics (attribution words, calendar-day movement, the moved
        # baseline column) end to end. Milestone 8 moves in the fixture, so the
        # attribution column has a row to leak through.
        pairs.append((os.path.join("ptc", "cycle_curr-review.html"),
                      PT_SECTIONS + ["Atribui\u00e7\u00e3o", "replanejamento", "Moveu (dias corridos)",
                                     "LB movida neste ciclo"]
                      + FORBID_PT_REVIEW + ["--forbid=\\b(replan|execution)\\b"]))
        subprocess.run(
            [sys.executable, os.path.join(HERE, "review.py"),
             os.path.join(ROOT, "fixtures", "positive.xml"),
             "--outdir", os.path.join(tmp, "ptp"), "--quiet", "--lang", "pt"],
            check=True, capture_output=True,
        )
        # The schedule with the four inputs missing, end to end, in both languages.
        for lang in ("en", "pt"):
            subprocess.run(
                [sys.executable, os.path.join(HERE, "review.py"),
                 os.path.join(ROOT, "fixtures", "bare.xml"),
                 "--outdir", os.path.join(tmp, "bare-" + lang), "--quiet", "--lang", lang],
                check=True, capture_output=True,
            )
        pairs.append((os.path.join("bare-en", "bare-review.html"), BARE_SECTIONS + FORBID))
        pairs.append((os.path.join("bare-pt", "bare-review.html"),
                      ["N\u00e3o h\u00e1 rede para se sustentar", "indispon\u00edvel"] + FORBID_PT))
        pairs.append((os.path.join("ptp", "positive-review.html"), PT_SECTIONS + FORBID_PT_REVIEW))
        # No path in any file written, sidecars included, and the tab title in the
        # report's own language.
        for folder, _, names in os.walk(tmp):
            for name in names:
                with open(os.path.join(folder, name), encoding="utf-8") as fh:
                    blob = fh.read()
                if tmp in blob or ROOT in blob:
                    out["failures"].append(f"privacy: {name} carries a local path")
        for rel, want in ((os.path.join("ptc", "cycle_prev--to--cycle_curr-cycle.html"),
                           "<title>Compara\u00e7\u00e3o de ciclo \u2014 Cycle fixture curr</title>"),
                          (os.path.join("pt", "cycle_curr-review.html"),
                           "<title>An\u00e1lise cr\u00edtica \u2014 Cycle fixture curr</title>"),
                          ("cycle_prev--to--cycle_curr-cycle.html",
                           "<title>Cycle comparison \u2014 Cycle fixture curr</title>")):
            with open(os.path.join(tmp, rel), encoding="utf-8") as fh:
                head = fh.read(600)
            if want not in head:
                out["failures"].append(f"report {rel}: the tab title is not in the report's language")
        # A scoped network gate, rendered: one side-branch pair must not raise the
        # absolute banner over the findings (0.7.2).
        import copy as _cp
        import parse_mspdi
        import report_data
        import report_html as _rh
        import run_checks as _rc
        gm = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "positive.xml"))
        gr = _rc.run(gm, _rc.DEFAULT_THRESHOLD_DAYS, _rc.DEFAULT_TOLERANCE_DAYS)
        gr = _cp.deepcopy(gr)
        gr["pairs"]["A1"] = gr["pairs"]["A1"][:1]
        gr["counts"]["A2"]["distinct_activities"] = 0
        gr["findings"]["A2"] = []
        keep = {gr["pairs"]["A1"][0]["successor_uid"], gr["pairs"]["A1"][0]["predecessor_uid"]}
        for t in gm["tasks"]:
            if t["uid"] in keep:
                t["critical"], t["total_slack_minutes"] = False, 4800.0
        for lang_, quiet_ in (("en", "Read this before any date"), ("pt", "Leia isto antes")):
            gp = report_data.build_review(gm, gr, lang=lang_)
            gpath = os.path.join(tmp, f"gate-{lang_}.html")
            _rh.write(gp, gpath)
            pairs.append((f"gate-{lang_}.html",
                          ["row 2" if lang_ == "en" else "linha 2", "--forbid=" + quiet_]))
        if not os.path.exists(os.path.join(tmp, "cycle_prev--to--cycle_curr-cycle-readings.json")):
            out["failures"].append("cycle: the readings sidecar was not written")
        # Executive synthesis injection: rebuild from embedded data, no recomputation.
        syn = os.path.join(tmp, "syn.txt")
        with open(syn, "w", encoding="utf-8") as fh:
            fh.write("First paragraph of a synthesis.\n\nSecond paragraph, with <b>no</b> markup interpreted.")
        target = os.path.join(tmp, "cycle_curr-review.html")
        if os.path.exists(target):
            p = subprocess.run([sys.executable, os.path.join(HERE, "inject_narrative.py"), target, syn,
                                "--who", "the test suite"], capture_output=True, text=True)
            if p.returncode != 0:
                out["failures"].append(f"synthesis: injection failed: {p.stderr.strip()}")
            else:
                with open(target, encoding="utf-8") as fh:
                    body = fh.read()
                if "Second paragraph" not in body or "the test suite" not in body:
                    out["failures"].append("synthesis: injected text or author missing from the report")
                if "<b>no</b>" in body:
                    out["failures"].append("synthesis: markup in the text was interpreted, not escaped")
        # The cycle report too, asserted on what the renderer DRAWS: the raw file
        # always carries the text inside its embedded data, so a check on the file
        # passed while the cycle page never showed the synthesis (fixed in 0.7.2).
        for rel, lang_word in (("cycle_prev--to--cycle_curr-cycle.html", "Executive synthesis"),
                               (os.path.join("ptc", "cycle_prev--to--cycle_curr-cycle.html"),
                                "S\u00edntese executiva")):
            target = os.path.join(tmp, rel)
            p = subprocess.run([sys.executable, os.path.join(HERE, "inject_narrative.py"), target, syn,
                                "--who", "the test suite"], capture_output=True, text=True)
            if p.returncode != 0:
                out["failures"].append(f"synthesis (cycle): injection failed: {p.stderr.strip()}")
            for i, (name, sections) in enumerate(pairs):
                if name == rel:
                    pairs[i] = (name, sections + [lang_word, "Second paragraph, with",
                                                  "the test suite"])
        for name, sections in pairs:
            path = os.path.join(tmp, name)
            if not os.path.exists(path):
                out["failures"].append(f"report: {name} was not produced")
                continue
            p = subprocess.run(
                [node, os.path.join(HERE, "test_render.js"), path, *sections],
                capture_output=True, text=True,
            )
            if p.returncode != 0:
                out["failures"].append(f"report {name}: {p.stderr.strip()}")
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            if "/*DATA*/" in body:
                out["failures"].append(f"report {name}: the data marker was not replaced")
            # No network, ever: it must open from an email attachment on a machine
            # with no connection and look the same.
            external = [
                u for u in re.findall(r'(?:src|href)="([^"]+)"', body)
                if u.startswith(("http", "//"))
            ]
            if external:
                out["failures"].append(
                    f"report {name}: external references break offline use: {external}"
                )
    return out


def example_checks() -> dict:
    """The fictitious road-works pair under examples/: every planted problem is found.

    The example is what a reader runs first, and its README lists what was planted
    so the report can be checked against it. This holds the two together: if the
    generator, the files or the engine drift apart, the list in the README stops
    being true and this fails. An installed copy of the skill does not carry the
    examples folder; there the check is skipped, and says so.
    """
    failures = []
    folder = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "examples")
    gen_path = os.path.join(folder, "make_exemplo.py")
    if not os.path.exists(gen_path):
        return {"failures": failures, "skipped": True}

    import importlib.util
    import compare_snapshots
    import forecast as forecast_mod
    import forensics as forensics_mod
    import network_quality as quality_mod
    import parse_mspdi
    import phasing as phasing_mod
    import report_data
    import run_checks

    spec = importlib.util.spec_from_file_location("make_exemplo", gen_path)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    out = gen.generate()
    paths = {}
    for name, body in out["files"].items():
        paths[name[-9:-4]] = path = os.path.join(folder, name)
        on_disk = None
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                on_disk = fh.read().replace("\r\n", "\n")   # a checkout may convert line ends
        if on_disk != body:
            failures.append(f"example: {name} is not what make_exemplo.py generates; run the generator")
    if failures:
        return {"failures": failures, "skipped": False}
    if gen.generate()["files"] != out["files"]:
        failures.append("example: the generator is not deterministic")

    P = gen.PLANTED
    uid = {r.key: r.uid for rev in out["snaps"] for r in out["snaps"][rev]["rows"]}
    prev, curr = parse_mspdi.parse(paths["rev03"]), parse_mspdi.parse(paths["rev04"])
    if not 150 <= prev["counts"]["tasks"] <= 250 or prev["counts"]["links"] < 150:
        failures.append(f"example: unexpected size {prev['counts']}")

    def fail(msg):
        failures.append("example: " + msg)

    # ---- each delivery on its own
    res_p = run_checks.run(prev, run_checks.DEFAULT_THRESHOLD_DAYS, run_checks.DEFAULT_TOLERANCE_DAYS)
    res_c = run_checks.run(curr, run_checks.DEFAULT_THRESHOLD_DAYS, run_checks.DEFAULT_TOLERANCE_DAYS)
    if res_p["blocking"] or res_c["blocking"]:
        fail("a blocking notice on a file built with a status date and a costed baseline")
    if any(c["marked_rows"] for c in res_p["counts"].values()):
        fail(f"rev03 should be clean on A1 to P, got {res_p['counts']}")
    oos = P["out_of_sequence"]["task"]
    pairs = [(a["successor_uid"], a["link_type"]) for a in res_c["pairs"]["A1"]]
    if pairs != [(uid[oos], "FS")]:
        fail(f"out of sequence: expected one A1 pair on the planted activity, got {res_c['pairs']['A1']}")
    if any(res_c["counts"][c]["marked_rows"] for c in CODES if c != "A1"):
        fail(f"rev04 should raise A1 only, got {res_c['counts']}")

    curve = phasing_mod.build(paths["rev04"], None)
    rec, tot = curve["reconciliation"], curve["totals"]
    if not curve["inputs"]["planned_available"] or tot["planned_to_date"] is None or tot["spi"] is None:
        fail("the planned curve is not available: the baseline cost is not read as time-phased")
    if rec["phasing_sum_equals_cost"] != rec["with_cost"] \
            or rec["phasing_to_status_equals_bcws"] != rec["bcws_comparable"] \
            or rec["earned_equals_bcwp"] != rec["bcwp_comparable"]:
        fail(f"the phasing does not reconcile with the file's own totals: {rec}")
    odd = next(t for t in curr["tasks"] if t["uid"] == uid[P["percent_vs_physical"]["task"]])
    if not odd["percent_complete"] - odd["physical_percent_complete"] >= 20 \
            or abs(tot["method_gap_points"] or 0) < 0.01:
        fail("percent complete against physical percent: the disagreement did not reach the method gap")
    # 0.8: the activity is named, not only the total gap; its pace gets no verdict.
    pvp = curve.get("percent_vs_physical") or {}
    if not pvp.get("rows") or pvp["rows"][0]["uid"] != odd["uid"] or (pvp["rows"][0]["share_of_gap_pct"] or 0) < 50:
        fail(f"percent vs physical: the activity behind the method gap is not named first: {pvp.get('rows', [])[:1]}")
    import resources as resources_mod
    prod_c = resources_mod.build(paths["rev04"], curr)
    pa = next((a for a in prod_c["activities"] if a["uid"] == odd["uid"]), None)
    if pa and pa["verdict_global"] != "inconsistent":
        fail(f"percent vs physical: the productivity verdict reads {pa['verdict_global']} on a measurement that disagrees with itself")

    quality = quality_mod.build(curr, paths["rev04"])
    by_code = {m["code"]: m for m in quality["metrics"]}
    for model, q in ((prev, None), (curr, quality)):
        if report_data.network_state(model, q)["state"] != "linked":
            fail(f"network state of {model['source']} is not 'linked'")
    open_ends = {uid[k] for k in P["no_successor"]}
    if {i["uid"] for i in by_code["Q1"]["items"]} != open_ends \
            or any(i["missing"] != "successor" for i in by_code["Q1"]["items"]):
        fail(f"missing logic: Q1 is not the planted open ends: {by_code['Q1']['items']}")
    if not open_ends <= {i["uid"] for i in by_code["Q6"]["items"]}:
        fail("high float: the open-ended activities are not in Q6")
    if by_code["Q7"]["count"] or by_code["Q9"]["count"] or by_code["Q5"]["count"]:
        fail("negative float, invalid dates or hard constraints in a schedule meant to be mostly healthy")

    fc = forecast_mod.build(curr, curve, None, None)
    rain = fc["rain_exposure"]
    if not fc["earned_schedule"]["available"] or not rain["readable"] \
            or not (rain["share_in_reserve_pct"] or 0) > 10:
        fail(f"earned schedule or rain exposure not readable: {fc['earned_schedule']} {rain}")

    # ---- the cycle
    cyc = compare_snapshots.compare(prev, curr)
    trend = {t["uid"]: t for t in cyc["trend"]}
    if sum(1 for t in cyc["trend"] if t["reading"] == "execution") < 5:
        fail("execution: fewer than five activities moved with actuals behind them")
    rp = P["replan"]["task"]
    if trend.get(uid[rp], {}).get("reading") != "replan" \
            or [r["uid"] for r in cyc["logic"]["constraints_added"]] != [uid[rp]]:
        fail("replan: the pushed forecast is not read as a replan with a constraint added")
    dc = cyc["duration_changed"]
    if [(r["uid"], r["duration_before_days"], r["duration_after_days"]) for r in dc] != \
            [(uid[P["duration"]["task"]], float(P["duration"]["before"]), float(P["duration"]["after"]))]:
        fail(f"duration: expected the one planted change, got {dc}")
    past = cyc["past_rewritten"]
    if [r["uid"] for r in past["actual_finish"]] != [uid[P["past_rewritten"]["task"]]] \
            or past["actual_start"] or past["percent_decreased"]:
        fail(f"past rewritten: expected one actual finish, got {past}")
    if [r["uid"] for r in cyc["baseline_moved"]] != [uid[P["rebaselined"]["task"]]]:
        fail(f"rebaselined: got {cyc['baseline_moved']}")
    if [r["uid"] for r in cyc["unmatched"]["inserted"]] != [uid[P["inserted"]]] \
            or [r["uid"] for r in cyc["unmatched"]["removed"]] != [uid[P["removed"]]]:
        fail(f"scope: got {cyc['unmatched']}")
    lg = cyc["logic"]
    if [(r["uid"], r["predecessor_uid"]) for r in lg["links_added"]] != \
            [(uid[P["link_added"][0]], uid[P["link_added"][1]])] \
            or [(r["uid"], r["predecessor_uid"]) for r in lg["links_removed"]] != \
            [(uid[P["link_removed"][0]], uid[P["link_removed"][1]])]:
        fail(f"links: added {lg['links_added']} removed {lg['links_removed']}")
    pf = cyc["project_finish"]
    viaduct = {u for k, u in uid.items() if k.startswith("oae.") or k == "ms.oae"}
    if not 7 <= (pf["delta_days"] or 0) <= 45 or len(viaduct & {n["uid"] for n in pf["current"]["chain"]}) < 5 \
            or uid[P["duration"]["task"]] not in {n["uid"] for n in pf["current"]["chain"]}:
        fail(f"project finish: not slipping some days along the viaduct: {pf['delta_days']}")
    fell = {r["uid"]: r for r in cyc["critical_path"]["float_fell_top"]}
    ms = fell.get(uid["ms.s3"])
    if not ms or ms["float_fell_days"] < 5 or ms["float_after_days"] < 0:
        fail(f"float erosion: the segment 3 milestone did not lose float: {ms}")
    codes = {w["code"] for w in cyc["warning_codes"]}
    if not {"baseline_moved", "scope", "past_rewritten"} <= codes or not codes & {"residue", "residue_named"} \
            or codes & {"same_status_date", "status_date_backwards", "slot_differs"}:
        fail(f"cycle warnings: {sorted(codes)}")

    fx = forensics_mod.build(curr, res_c, prev, cyc)
    trp = next((m for m in fx["milestones"] if m["id"] and m["name"].startswith("Termo de Recebimento")), None)
    if not trp or not trp["origin"] or not trp["amplifier"] \
            or trp["amplifier"]["id"] != next(t["id"] for t in curr["tasks"]
                                               if t["uid"] == uid[P["duration"]["task"]]):
        fail(f"forensics: the final milestone's delay is not traced to the viaduct: {trp and trp['amplifier']}")

    # ---- deadlines (0.8): each milestone against its deadline, right after the verdict.
    from datetime import date as _date
    dl = report_data.deadline_rows(fc, fx)
    id_of = {t["uid"]: t["id"] for t in curr["tasks"]}
    oae = id_of.get(uid["ms.oae"])
    if not dl or dl["with_deadline"] < 5:
        fail(f"deadlines: the milestones' deadlines were not read: {dl and dl['with_deadline']}")
    else:
        if not dl["tightest"] or dl["tightest"]["id"] != oae:
            fail(f"deadlines: the tightest margin is not the viaduct milestone: {dl['tightest']}")
        for r in dl["rows"]:
            if r["deadline"] and r["finish"] and r["margin_days"] != \
                    (_date.fromisoformat(r["deadline"]) - _date.fromisoformat(r["finish"])).days:
                fail(f"deadlines: row {r['id']} margin is not deadline minus finish")
            if r["margin_days"] is not None and r["p80_margin_days"] != r["margin_days"] - dl["p80_days"]:
                fail(f"deadlines: row {r['id']} P80 margin is not the margin minus the P80 slippage")
        row_oae = next((r for r in dl["rows"] if r["id"] == oae), {})
        if not row_oae.get("origin_id") or row_oae["origin_id"] == oae:
            fail("deadlines: the viaduct milestone's row does not name where its delay starts")
        # The cycle report opens C1 with the same table and sentences, in reading order.
        pay = report_data.build_cycle(cyc, lang="pt", deadlines=dl)
        if [s["code"] for s in pay["sections"]] != ["C1", "C5", "C3", "C4", "C2", "C6"]:
            fail("cycle order: the sections are not deadlines, integrity, replanning, float, quality")
        c1 = pay["sections"][0]
        if not c1["lists"] or c1["lists"][0]["count"] != len(dl["rows"]) \
                or not c1["reading"] or "data limite" not in c1["reading"][0] \
                or pay["readings"]["c1"] != c1["reading"]:
            fail("cycle order: C1 does not open with the milestones against their deadline")
        if pay["meta"]["finish_delta_days"] != cyc["project_finish"]["delta_days"]:
            fail("cycle order: the hero is not the project finish movement")
        # What to ask the contractor: every planted evidence row, integrity first, and
        # no question on a row that was only pushed by its predecessor.
        pay = report_data.build_cycle(cyc, lang="pt", deadlines=dl, model=curr)
        import i18n as i18n_mod
        dm = pay["demands"]
        asked = {x["id"] for x in dm if x["id"] is not None}
        if not dm or dm[0]["group"] != i18n_mod.cycle_text("pt")["dm_g_integrity"]:
            fail("demands: the list does not open with the integrity of the measurement")
        if id_of[uid[P["duration"]["task"]]] not in asked:
            fail("demands: the planted duration change is not asked about")
        if id_of[uid["fim.desmob"]] in asked:
            fail("demands: a row pushed only by its predecessor is asked to justify itself")
        if not any("linha de base" in x["text"] and "coincidir" in x["text"] for x in dm):
            fail("demands: an actual finish rewritten onto the baseline date is not called out")
    return {"failures": failures, "skipped": False}


def main() -> int:
    # No test may read or write the real ~/.cronoaudit, and no child run may stop to
    # ask the mode question when the tests are started from a terminal (the child
    # inherits it). Every run below sees a throwaway preference of "off"; the mode
    # tests further down use folders of their own.
    with tempfile.TemporaryDirectory() as cfg_home:
        os.environ["CRONOAUDIT_CONFIG_DIR"] = cfg_home
        with open(os.path.join(cfg_home, "config.json"), "w", encoding="utf-8") as fh:
            fh.write('{"secret": "off"}\n')
        return run_all()


def mode_checks() -> list:
    """Modes: the stored preference, and what review.py does with it.

    The point of every case is the same: a run asked to be secret must not read the
    schedule, and a preference that cannot be read must not become "free, silently".
    """
    import io

    import cronoaudit_config as cfg
    import i18n
    import review

    failures = []
    xml = os.path.join(ROOT, "fixtures", "positive.xml")
    saved = os.environ.get("CRONOAUDIT_CONFIG_DIR")

    def engine(args, home, agent=False):
        # The tests may themselves run inside an agent (Claude Code sets these for
        # every command it runs). Secret mode refuses to start there, which is one of
        # the cases below; every other case runs as a person at a terminal would.
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION")}
        env.update(CRONOAUDIT_CONFIG_DIR=home, CRONOAUDIT_WORK_DIR=work)
        if agent:
            env["CLAUDE_CODE_CHILD_SESSION"] = "1"
        # DEVNULL: not a terminal, whatever started the tests.
        return subprocess.run([sys.executable, os.path.join(HERE, "review.py")] + args,
                              capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            home = os.path.join(tmp, "home", ".cronoaudit")   # does not exist yet
            out = os.path.join(tmp, "out")
            work = os.path.join(tmp, "work")
            os.environ["CRONOAUDIT_CONFIG_DIR"] = home

            # ---- the file: missing, set, read back, other keys kept, corrupt, invalid
            st = cfg.load()
            if st["secret"] != "ask" or st["status"] != "missing":
                failures.append(f"modes: a missing file is not the factory default: {st}")
            if os.path.exists(home):
                failures.append("modes: reading the preference created the folder")
            for value in ("on", "off", "ask"):
                path = cfg.set_secret(value)
                st = cfg.load()
                if st["secret"] != value or st["status"] != "ok" or path != cfg.config_path():
                    failures.append(f"modes: set {value!r} did not read back: {st}")
            raw = open(cfg.config_path(), "rb").read()
            if raw.startswith(b"\xef\xbb\xbf") or json.loads(raw.decode("utf-8")) != {"secret": "ask"}:
                failures.append(f"modes: the file is not plain UTF-8 JSON with the one key: {raw!r}")
            if [f for f in os.listdir(home) if f != "config.json"]:
                failures.append(f"modes: the atomic write left a file behind: {os.listdir(home)}")
            try:
                cfg.set_secret("maybe")
                failures.append("modes: an unknown value was stored")
            except ValueError:
                pass
            with open(cfg.config_path(), "w", encoding="utf-8") as fh:
                fh.write('{"secret": "off", "other": 7}')
            cfg.set_secret("on")
            if json.load(open(cfg.config_path(), encoding="utf-8")) != {"secret": "on", "other": 7}:
                failures.append("modes: storing the preference dropped another key of the file")
            # A byte-order mark in front, as a Windows editor leaves it, is still readable.
            with open(cfg.config_path(), "wb") as fh:
                fh.write(b"\xef\xbb\xbf" + b'{"secret": "OFF"}')
            if cfg.load()["secret"] != "off":
                failures.append("modes: a file with a byte-order mark, or an upper-case value, was not read")
            for bad, want in (("{not json", "corrupt"), ("", "corrupt"), ("[1, 2]", "corrupt"),
                              ('{"secret": "yes"}', "invalid"), ('{"secret": true}', "invalid"),
                              ('{"other": 1}', "missing")):
                with open(cfg.config_path(), "w", encoding="utf-8") as fh:
                    fh.write(bad)
                st = cfg.load()
                if st["secret"] != "ask" or st["status"] != want:
                    failures.append(f"modes: {bad!r} should be ask/{want}, got {st['secret']}/{st['status']}")
            # A corrupt file is said, not swallowed, and is replaced by the next set.
            with open(cfg.config_path(), "w", encoding="utf-8") as fh:
                fh.write('{"secret": "yes"}')
            r = engine(["--config", "--lang", "en"], home)
            if r.returncode != 0 or not r.stdout.startswith("secret: ask\n") or "not ask, on or off" not in r.stdout:
                failures.append(f"modes: --config did not report an invalid file as ask: {r.stdout!r}")
            with open(cfg.config_path(), "w", encoding="utf-8") as fh:
                fh.write("{not json")
            r = engine([xml, "--outdir", out, "--quiet", "--lang", "en"], home)
            if r.returncode != 0 or "could not be read" not in r.stderr or "FREE mode" not in r.stderr:
                failures.append(f"modes: a corrupt file was not said on stderr before going on: {r.stderr!r}")
            r = engine(["--secret", "off"], home)
            if r.returncode != 0 or not r.stdout.startswith("secret: off\n") or cfg.load()["status"] != "ok":
                failures.append(f"modes: --secret off did not replace a corrupt file: {r.stdout!r} {r.stderr!r}")

            # ---- the decision table
            for (fs, ff, pref, tty), want in {
                    (True, False, "off", False): "secret", (True, False, "ask", True): "secret",
                    (False, True, "on", False): "free", (False, True, "ask", True): "free",
                    (False, False, "on", True): "secret", (False, False, "on", False): "secret",
                    (False, False, "off", True): "free", (False, False, "off", False): "free",
                    (False, False, "ask", True): "ask", (False, False, "ask", False): "notice"}.items():
                got = cfg.decide(fs, ff, pref, tty)
                if got != want:
                    failures.append(f"modes: decide(secret={fs}, free={ff}, {pref}, tty={tty}) gave {got}, not {want}")

            # ---- `--secret` must not swallow the schedule that follows it
            for argv, want in ((["--secret", "a.xml"], ["--secret=run", "a.xml"]),
                               (["a.xml", "--secreto"], ["a.xml", "--secret=run"]),
                               (["--secret", "ON"], ["--secret=on"]),
                               (["--secreto=Ask"], ["--secret=ask"]),
                               (["a.xml", "--free"], ["a.xml", "--free"])):
                if review.normalise_mode_args(argv) != want:
                    failures.append(f"modes: {argv} normalised to {review.normalise_mode_args(argv)}")

            # ---- --secret started by an agent stops without reading. The file named
            # does not exist: had the engine gone as far as looking for it, the
            # message would say so.
            def nothing_written():
                return not os.path.exists(out) or not os.listdir(out)
            def no_work():
                return not os.path.exists(work) or not os.listdir(work)
            import shutil
            shutil.rmtree(out, ignore_errors=True)
            for args in ([xml, "--secret", "--outdir", out], ["--secret", xml, "--outdir", out],
                         [xml, "--secreto", "--outdir", out, "--lang", "pt"]):
                r = engine(args, home, agent=True)   # the stored preference is "off": the flag wins
                if r.returncode != review.EXIT_SECRET or r.stdout.strip() or not nothing_written() \
                        or not no_work():
                    failures.append(f"modes: {args[:2]} inside an agent did not stop clean: rc {r.returncode}, "
                                    f"stdout {r.stdout[:80]!r}, outdir {os.path.exists(out)}")
                if "Nothing was read" not in r.stderr and "Nada foi lido" not in r.stderr:
                    failures.append("modes: the stop message does not say that nothing was read")
                if "CLAUDE_CODE_CHILD_SESSION" not in r.stderr:
                    failures.append("modes: the stop message does not name what showed an agent started it")
            r = engine([os.path.join(tmp, "no-such-file.xml"), "--secret", "--lang", "en"], home, agent=True)
            if r.returncode != review.EXIT_SECRET or "no such file" in (r.stderr + r.stdout) \
                    or "not found" in (r.stderr + r.stdout):
                failures.append("modes: --secret inside an agent looked for the schedule before stopping")
            if "SECRET mode was requested" not in r.stderr or "SECRETO" in r.stderr:
                failures.append("modes: with --lang en the stop message is not in English only")
            r = engine([xml, "--secret", "--free"], home)
            if r.returncode != 2 or not nothing_written():
                failures.append("modes: --secret with --free was not rejected")
            # ---- run by a person, --secret runs: a work folder, nothing beside the file
            r = engine([xml, "--secret", "--outdir", out, "--quiet", "--lang", "en"], home)
            if r.returncode != 0 or not nothing_written() or no_work() or "Work folder" not in r.stdout:
                failures.append(f"modes: --secret run by a person did not write a work folder only: "
                                f"rc {r.returncode} {r.stderr[-200:]!r}")

            # ---- stored "on" behaves as --secret; --free is the only way through it
            engine(["--secret", "on"], home)
            r = engine([xml, "--outdir", out, "--quiet"], home, agent=True)
            if r.returncode != review.EXIT_SECRET or not nothing_written() or cfg.config_path() not in r.stderr:
                failures.append(f"modes: a stored 'on' inside an agent did not stop and name the file: rc {r.returncode}")
            shutil.rmtree(work, ignore_errors=True)
            r = engine([xml, "--outdir", out, "--quiet"], home)
            if r.returncode != 0 or not nothing_written() or no_work():
                failures.append(f"modes: a stored 'on' did not run in secret mode: rc {r.returncode}")
            r = engine([xml, "--outdir", out, "--quiet", "--free"], home)
            if r.returncode != 0 or nothing_written() or r.stderr.strip():
                failures.append(f"modes: --free did not run, quietly, over a stored 'on': {r.stderr!r}")

            # ---- "ask" with nobody to answer: one line on stderr, then the run
            shutil.rmtree(out, ignore_errors=True)
            engine(["--secret", "ask"], home)
            r = engine([xml, "--outdir", out, "--quiet", "--lang", "en"], home)
            lines = [ln for ln in r.stderr.splitlines() if ln.strip()]
            if r.returncode != 0 or nothing_written():
                failures.append(f"modes: 'ask' with no terminal blocked the run: rc {r.returncode} {r.stderr!r}")
            if len(lines) != 1 or "FREE mode" not in lines[0] or "--secret" not in lines[0]:
                failures.append(f"modes: 'ask' with no terminal did not say one line on stderr: {lines}")
            if "FREE mode" in r.stdout:
                failures.append("modes: the free-mode line went to stdout, where a program reads results")
            # "off" says nothing at all.
            engine(["--secret", "off"], home)
            r = engine([xml, "--outdir", out, "--quiet"], home)
            if r.returncode != 0 or r.stderr.strip():
                failures.append(f"modes: a stored 'off' still spoke: {r.stderr!r}")

            # ---- the question itself, answered. In-process, with the streams swapped.
            def answer(text):
                cfg.set_secret("ask")
                old_in, old_err = sys.stdin, sys.stderr
                sys.stdin, sys.stderr = io.StringIO(text), io.StringIO()
                try:
                    mode = review.ask_mode(cfg.load(), i18n.modes_text("pt"), ["pt"])
                    return ("go" if mode == "free" else mode), sys.stderr.getvalue()
                except SystemExit as exc:
                    return exc.code, sys.stderr.getvalue()
                finally:
                    sys.stdin, sys.stderr = old_in, old_err
            for text, want, pref in (("s\n", "go", "ask"), ("livre\n", "go", "ask"), ("y\n", "go", "ask"),
                                     ("secreto\n", "secret", "ask"), ("n\n", 1, "ask"),
                                     ("nunca\n", "go", "off"), ("\n\nwhat\n", 1, "ask"), ("", 1, "ask"),
                                     ("talvez\nsim\n", "go", "ask")):
                got, shown = answer(text)
                if got != want or cfg.load()["secret"] != pref:
                    failures.append(f"modes: answering {text!r} gave {got} with preference "
                                    f"{cfg.load()['secret']}, not {want} with {pref}")
                if "Modo LIVRE: o que o agente ler vai para o provedor dele. Continuar?" not in shown:
                    failures.append("modes: the question is not the agreed sentence")

            # ---- every mode string exists in both languages, with the same placeholders
            for key, en in i18n.MODES["en"].items():
                pt = i18n.MODES["pt"].get(key)
                if pt is None or sorted(re.findall(r"\{(\w+)\}", en)) != sorted(re.findall(r"\{(\w+)\}", pt)):
                    failures.append(f"modes: the string {key!r} is missing or takes other values in pt")
            if set(i18n.MODES["pt"]) - set(i18n.MODES["en"]):
                failures.append("modes: pt has strings en does not")
    finally:
        if saved is None:
            os.environ.pop("CRONOAUDIT_CONFIG_DIR", None)
        else:
            os.environ["CRONOAUDIT_CONFIG_DIR"] = saved
    return failures


# ---------------------------------------------------------------------------
# Secret mode (experimental). Three properties, each tested here:
#   equality  the coded output decodes to exactly what free mode writes
#   no leak   nothing of the file's identity is anywhere in the work folder
#   guard     the Claude Code hook allows the session's work and blocks the rest
# `secret_roundtrip` is also what test_secret_real.py runs on a real export, so it
# never puts a value from the file into a message when `redact` is set.
# ---------------------------------------------------------------------------
_REAL_DATE_SHAPES = re.compile(
    r"(?<![\w\d])(?:19|20|21)\d\d-[01]\d-[0-3]\d"      # ISO day
    r"|(?<![\w\d/])[0-3]\d/[01]\d/(?:19|20|21)\d\d"     # dd/mm/yyyy
    r"|(?<![\w\d\-])(?:19|20|21)\d\d-[01]\d(?![\d\-])"  # yyyy-mm
    r"|(?<![\w\d])(?:19|20|21)\d\d(?=:(?!\d))"          # "2026: ..."
    r"|(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|"
    r"dezembro|January|February|March|April|June|July|August|September|October|November|"
    r"December)\s+(?:de\s+)?(?:19|20|21)\d\d", re.I)


def _secret_env(home: str, agent: bool = False) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION")}
    env["CRONOAUDIT_CONFIG_DIR"] = home
    env.pop("CRONOAUDIT_WORK_DIR", None)
    if agent:
        env["CLAUDE_CODE_CHILD_SESSION"] = "1"
    return env


def _payload_of(path: str) -> dict:
    import inject_narrative
    with open(path, encoding="utf-8") as fh:
        return inject_narrative.extract(fh.read())


def _scan_text(path: str) -> str:
    """What a file says, for the leak test. For a report, the embedded data and the
    tab title: the rest is the template, the same public code for every schedule."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        body = fh.read()
    if path.endswith(".html"):
        m = re.search(r"const DATA = (\{.*?\});\n", body, re.S)
        t = re.search(r"<title>.*?</title>", body, re.S)
        return (m.group(1) if m else body) + "\n" + (t.group(0) if t else "")
    return body


def _forms(value: str) -> set:
    import html as html_mod
    j = json.dumps(value, ensure_ascii=False)[1:-1]
    return {value, j, j.replace("</", "<\\/"), html_mod.escape(value), html_mod.escape(value, quote=False)}


def _money_forms(v) -> set:
    import secret_codec
    out = set()
    if isinstance(v, bool) or not isinstance(v, (int, float)) or abs(v) < 10000:
        return out
    out.add(repr(v))
    if float(v).is_integer():
        out.add(str(int(v)))
    for d in (0, 2):
        for lang in ("pt", "en"):
            out.add(secret_codec.fnum(v, d, lang))
    return out


def _money_values(obj, keys) -> list:
    found, stack = [], [(None, obj)]
    while stack:
        k, o = stack.pop()
        if isinstance(o, dict):
            stack.extend(o.items())
        elif isinstance(o, list):
            stack.extend((k, x) for x in o)
        elif k in keys and isinstance(o, (int, float)) and not isinstance(o, bool):
            found.append(o)
    return found


_VOCABULARY = {}


def _program_vocabulary(avoid: list) -> str:
    """Everything cronoaudit itself writes in a secret run, over a fixture that is not
    the schedule under test: the coded work folder (whole files, template included),
    stdout, stderr and the finish line. Fixture names are coded there, so what is
    left legible is program text."""
    fixture = next(n for n in ("bare.xml", "negative.xml") if n not in avoid)
    if fixture in _VOCABULARY:
        return _VOCABULARY[fixture]
    import shutil
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.path.join(tmp, "orig")
        os.makedirs(orig)
        src = os.path.join(orig, fixture)
        shutil.copyfile(os.path.join(ROOT, "fixtures", fixture), src)
        env = _secret_env(os.path.join(tmp, "cfg"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "review.py"), src, "--secret",
                            "--workdir", os.path.join(tmp, "work")], capture_output=True, text=True,
                           env=env, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        parts += [r.stdout, r.stderr]
        work = os.path.join(tmp, "work", os.listdir(os.path.join(tmp, "work"))[0])
        f = subprocess.run([sys.executable, os.path.join(HERE, "secret_decode.py"), "finish", work,
                            "--no-open", "--vault-only"], capture_output=True, text=True, env=env,
                           encoding="utf-8", errors="replace")
        parts += [f.stdout, f.stderr]
        for folder, _d, fnames in os.walk(work):
            for fname in fnames:
                parts.append(fname)
                with open(os.path.join(folder, fname), encoding="utf-8", errors="replace") as fh:
                    parts.append(fh.read())
    _VOCABULARY[fixture] = "\n".join(parts)
    return _VOCABULARY[fixture]


def secret_roundtrip(files: list, tmp: str, redact: bool = False) -> dict:
    """Free run and secret run of the same files; decode; compare; look for leaks.

    Returns {"failures": [...], "stats": {...}}. With `redact`, a failure says what
    kind and how many, never which value.
    """
    import shutil

    import secret_codec
    import secret_decode

    failures, stats = [], {"sidecars": 0, "reports": 0, "values_equal": 0, "leak_values": 0,
                           "leak_hits": 0, "texts_checked": 0, "money_checked": 0}

    def fail(kind, detail=""):
        failures.append(kind if (redact or not detail) else f"{kind}: {detail}")

    orig = os.path.join(tmp, "orig")
    os.makedirs(orig, exist_ok=True)
    local = []
    for f in files:
        dst = os.path.join(orig, os.path.basename(f))
        shutil.copyfile(f, dst)
        local.append(dst)
    home = os.path.join(tmp, "cfg")
    workroot = os.path.join(tmp, "work")
    free_dir = os.path.join(tmp, "free")
    env = _secret_env(home)
    r = subprocess.run([sys.executable, os.path.join(HERE, "review.py"), *local, "--free",
                        "--outdir", free_dir, "--quiet"], capture_output=True, text=True,
                       env=env, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail("secret: the free run failed")
        return {"failures": failures, "stats": stats}
    sec = subprocess.run([sys.executable, os.path.join(HERE, "review.py"), *local, "--secret",
                          "--workdir", workroot], capture_output=True, text=True, env=env,
                         stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    if sec.returncode != 0 or not os.path.isdir(workroot) or len(os.listdir(workroot)) != 1:
        fail("secret: the secret run failed", "" if redact else sec.stderr[-300:])
        return {"failures": failures, "stats": stats}
    work = os.path.join(workroot, os.listdir(workroot)[0])
    with open(os.path.join(work, "cronoaudit-secret.json"), encoding="utf-8") as fh:
        run_id = json.load(fh)["run"]
    vault_run = os.path.join(home, "vault", run_id)
    with open(os.path.join(vault_run, "back.json"), encoding="utf-8") as fh:
        codec = secret_codec.Codec.from_back_table(json.load(fh))
    with open(os.path.join(vault_run, "run.json"), encoding="utf-8") as fh:
        run = json.load(fh)
    import secret_mode

    # ---- 1. equality, sidecar by sidecar: generic decoding alone, no lookup of
    # the real output except the withheld series, which by design is not coded.
    for name in sorted(os.listdir(free_dir)):
        if not name.endswith(".json"):
            continue
        coded_name = secret_mode.rename(name, local)
        with open(os.path.join(free_dir, name), encoding="utf-8") as fh:
            free = json.load(fh)
        with open(os.path.join(work, coded_name), encoding="utf-8") as fh:
            coded = json.load(fh)
        decoded = codec.decode_obj(coded)
        if name.endswith("-review-forecast.json"):
            for path in secret_codec.LEGIBILITY["withheld"]:
                if path[0] == "forecast":
                    secret_codec.restore(decoded, free, path[1:])
        if decoded != free:
            eq, df = secret_decode.count_leaves(decoded, free)
            fail("secret equality: a sidecar did not decode to the free run", f"{name}, {df} values")
        else:
            stats["sidecars"] += 1

    # ---- 2. equality of the report, after a fake agent wrote a synthesis in codes
    names = [n for n in os.listdir(free_dir) if n.endswith(".html")]
    review_coded = next(c for c, real in run["html"].items() if real.endswith("-review.html"))
    coded_payload = _payload_of(os.path.join(work, review_coded))
    some_task = next((t["name"] for f in (coded_payload.get("findings") or []) for t in f.get("items") or []
                      if t.get("name")), None) or next(iter(codec.back))
    real_name = codec.decode_text(some_task)
    syn = os.path.join(work, "synthesis.txt")
    with open(syn, "w", encoding="utf-8") as fh:
        fh.write(f"The activity {some_task} finishes on D+0400 and is worth {secret_codec.MONEY_MARK}"
                 f"{secret_codec.fnum(1234567.0 * codec.k, 2, codec.lang)}.\n\nSecond paragraph.")
    subprocess.run([sys.executable, os.path.join(HERE, "inject_narrative.py"),
                    os.path.join(work, review_coded), syn, "--who", "the test suite"],
                   check=True, capture_output=True)
    fin = subprocess.run([sys.executable, os.path.join(HERE, "secret_decode.py"), "finish", work,
                          "--no-open"], capture_output=True, text=True, env=env,
                         encoding="utf-8", errors="replace")
    if fin.returncode != 0 or "check passed" not in fin.stdout:
        fail("secret equality: finish did not pass its own check", fin.stdout[-200:] + fin.stderr[-200:])
    for name in names:
        free_p = _payload_of(os.path.join(free_dir, name))
        dec_p = _payload_of(os.path.join(vault_run, name))
        beside = os.path.join(orig, name)
        if not os.path.exists(beside):
            fail("secret: the decoded report was not written beside the original", name)
        narrative = dec_p.pop("narrative", None)
        free_p.pop("narrative", None)
        # The one normalisation: the time the report was generated. Two runs, two
        # minutes; it is not a finding.
        for p in (free_p, dec_p):
            (p.get("meta") or {}).pop("generated", None)
        if dec_p != free_p:
            eq, df = secret_decode.count_leaves(dec_p, free_p)
            fail("secret equality: a decoded report differs from the free run", f"{name}, {df} values")
        else:
            stats["reports"] += 1
            stats["values_equal"] += secret_decode.count_leaves(dec_p, free_p)[0]
        if name.endswith("-review.html"):
            text = (narrative or {}).get("text", "")
            want_day = codec._from_day(400)
            want_day = want_day.strftime("%d/%m/%Y" if codec.lang == "pt" else "%Y-%m-%d")
            want_money = secret_codec.fnum(1234567.0, 2, codec.lang)
            if real_name not in text or want_day not in text or want_money not in text:
                fail("secret equality: the synthesis did not decode to real name, date and money")

    # ---- 3. no leak: every text, date and money figure of the files, anywhere
    texts = set()
    for f in local:
        texts |= {v for _c, v in secret_codec.collect_xml(f)}
        texts |= {os.path.basename(f), os.path.splitext(os.path.basename(f))[0]}
    # Independently of the codec's own collection: every element text with a
    # letter that the boundary does not declare legible.
    import xml.etree.ElementTree as ET
    dates, costs = set(), []
    cost_tags = {"Cost", "BCWS", "BCWP", "ACWP", "FixedCost", "ActualCost", "RemainingCost",
                 "BaselineCost", "CostVariance"}
    for f in local:
        for _ev, el in ET.iterparse(f):
            tag = el.tag.rsplit("}", 1)[-1]
            t = (el.text or "").strip()
            if t:
                if secret_codec.eligible(t) and not secret_codec.format_legible(t) \
                        and tag not in secret_codec.LEGIBILITY["legible_tags"]:
                    texts.add(t)
                m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", t)
                if m:
                    dates.add(t[:10])
                    dates.add(f"{m.group(3)}/{m.group(2)}/{m.group(1)}")
                if tag in cost_tags:
                    try:
                        costs.append(float(t))
                    except ValueError:
                        pass
            el.clear()
    real_money = []
    for name in os.listdir(os.path.join(vault_run, "real")):
        p = os.path.join(vault_run, "real", name)
        obj = _payload_of(p) if name.endswith(".html") else json.load(open(p, encoding="utf-8"))
        real_money += _money_values(obj, secret_codec.LEGIBILITY["money_keys"])
    money_forms = set()
    for v in costs + real_money:
        money_forms |= _money_forms(v)
    stats["texts_checked"] = len(texts)
    stats["money_checked"] = len(money_forms)
    text_forms = set()
    for t in texts:
        text_forms |= _forms(t)
    rx_text = re.compile(r"(?<!\w)(?:" + secret_codec._trie_pattern(sorted(text_forms, key=len, reverse=True))
                         + r")(?!\w)") if text_forms else None
    # Not glued to a letter either: a token is six hex characters (T·a12345), and
    # five digits inside one matched a real figure by chance on the real export.
    rx_money = re.compile(r"(?<![\w.,])(?:" + secret_codec._trie_pattern(sorted(money_forms, key=len, reverse=True))
                          + r")(?![\d]|[.,]\d)") if money_forms else None
    rx_dates = re.compile(r"(?<![\d\w])(?:" + secret_codec._trie_pattern(sorted(dates, key=len, reverse=True))
                          + r")(?!\d)") if dates else None
    # The original's folder and the run's vault folder. The cronoaudit folder itself
    # is named on purpose, in the deny rule of .claude/settings.json (as ~/.cronoaudit
    # in a real installation); its location is documented, not secret.
    paths = [orig, os.path.realpath(orig), vault_run, os.path.realpath(vault_run)]
    surfaces = []
    for folder, _dirs, fnames in os.walk(work):
        for fname in fnames:
            surfaces.append((fname, _scan_text(os.path.join(folder, fname))))
            surfaces.append(("file name", fname))
    surfaces += [("stdout", sec.stdout), ("stderr", sec.stderr), ("finish", fin.stdout + fin.stderr)]
    # Two kinds of coincidence are not leaks, and are told apart without looking at
    # the value:
    #  - program vocabulary: a real text that is also a word of cronoaudit's own
    #    output (a label, a key, the guard's code). Such a word is in the work folder
    #    of ANY schedule. It is excused only if it appears in the coded output of a
    #    different schedule run through the same pipeline; that output holds no
    #    names of this file, so the excuse cannot hide one of them.
    #  - a coded figure equal by chance to a real one: money times k can land on
    #    another real figure. A money hit is excused only if the same string is a
    #    form of what the codec must write for some real figure (real times k). A
    #    real figure leaking unscaled is not such a form, so it still fails; the
    #    deliberate-break check (scaling switched off) proves it.
    vocabulary = _program_vocabulary([os.path.basename(f) for f in files])
    # What the codec should have written for each real figure, computed here from
    # the real output and k, not read from the work folder: a codec that forgot to
    # scale would otherwise excuse its own leak.
    coded_money = set()
    for v in costs + real_money:
        coded_money |= _money_forms(codec.scale(v))
        for d in (0, 2):
            coded_money.add(secret_codec.fnum(round(v, d) * codec.k, d, codec.lang))
    hits = {"text": {}, "date": {}, "money": {}, "date shape": 0, "path": 0}
    excused = {"vocabulary": 0, "coded figure": 0}
    for label, blob in surfaces:
        for kind, rx in (("text", rx_text), ("date", rx_dates), ("money", rx_money)):
            if not rx:
                continue
            for v in set(rx.findall(blob)):
                if kind == "text" and re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", vocabulary):
                    excused["vocabulary"] += 1
                    continue
                if kind == "money" and v in coded_money:
                    excused["coded figure"] += 1
                    continue
                hits[kind].setdefault(v, label)
        hits["date shape"] += len(_REAL_DATE_SHAPES.findall(blob))
        hits["path"] += sum(1 for p in paths if p in blob)
    stats["excused"] = excused
    stats["hit_detail"] = []
    for kind in ("text", "date", "money"):
        if hits[kind]:
            stats["leak_values"] += len(hits[kind])
            # Kind, length and where: enough to diagnose, never the value itself.
            stats["hit_detail"] += [(kind, len(v), where) for v, where in sorted(hits[kind].items())]
            fail(f"secret leak: {len(hits[kind])} {kind} value(s) of the file found in the work folder or output",
                 ", ".join(sorted(hits[kind])[:5]))
    for kind in ("date shape", "path"):
        if hits[kind]:
            stats["leak_hits"] += hits[kind]
            fail(f"secret leak: {hits[kind]} {kind} occurrence(s) in the work folder or output")

    # ---- 4. what an agent reads rendered: the coded report runs, and shows no real date
    import shutil as _sh
    node = _sh.which("node")
    if node:
        for c in run["html"]:
            p = subprocess.run([node, os.path.join(HERE, "test_render.js"), os.path.join(work, c),
                                r"--forbid=(?:19|20)\d\d-[01]\d-[0-3]\d|[0-3]\d/[01]\d/(?:19|20)\d\d"],
                               capture_output=True, text=True)
            if p.returncode != 0:
                fail("secret: a coded report does not render, or shows a real date", "" if redact else p.stderr[-200:])
    return {"failures": failures, "stats": stats}


def secret_unit_checks() -> list:
    """The codec on its own: collisions, money in prose, the boundary's tripwire."""
    from datetime import date

    import narrative
    import secret_codec as sc
    failures = []
    # Collisions: at two hex digits, 300 names in one category must collide, and
    # every one must still get its own token and come back.
    c = sc.Codec(b"k" * 32, date(2024, 1, 1), 3.3, width=2, lang="pt")
    names = [f"Atividade número {i}" for i in range(200)]
    c.add([("T", n) for n in names])
    if c.collisions == 0 or len(set(c.tokens.values())) != len(names):
        failures.append(f"secret codec: collisions not exercised or not resolved ({c.collisions})")
    for n in names:
        if c.decode_text(c.encode_text(f"x {n} y")) != f"x {n} y":
            failures.append("secret codec: a name did not survive a collision round trip")
            break
    # Persisted table: a codec rebuilt from the table gives the same tokens, so rev03
    # and rev04 read the same codes.
    c2 = sc.Codec(b"k" * 32, date(2024, 1, 1), 3.3, dict(c.tokens), width=2, lang="pt")
    c2.add([("T", "Nova atividade")] + [("T", n) for n in names])
    if any(c2.tokens[n] != c.tokens[n] for n in names):
        failures.append("secret codec: a persisted token changed when new names were added")
    # Money written into a sentence by the engine: the earned-before-plan reading.
    payload = {"lang": "pt", "meta": {}, "findings": [],
               "scurve": {"bac": 1000000.0, "totals": {},
                          "periods": [{"period": "2026-01", "planned": 0, "earned": 123456.78},
                                      {"period": "2026-02", "planned": 50000.0, "earned": 1000.0}]}}
    readings = narrative.build(payload, "pt")
    real_sentence = next((x for x in readings.get("scurve", []) if "123.457" in x), None)
    if real_sentence is None:
        failures.append("secret codec: the earned-before-plan reading did not fire on its probe")
    else:
        coded = {k: list(v) for k, v in readings.items()}
        n = sc.mark_prose_money(coded, payload, "pt", c)
        enc = c.encode_obj(coded)
        if n != 1 or "123.457" in json.dumps(enc, ensure_ascii=False):
            failures.append("secret codec: the money in the earned-before-plan reading was not coded")
        if c.decode_obj(enc) != readings:
            failures.append("secret codec: the earned-before-plan reading did not decode back")
    # Every shape of date, and the year key, round trip and change.
    probe = {"a": "2026-10-30T17:00:00", "b": "30/10/2026", "c": "2026-10", "year": 2027,
             "d": "2026: activities without reserve", "e": "between 2026-01-31 and 2026-02-01",
             "cost": 1234.5, "planned": 7, "pct": 12.5}
    enc = c.encode_obj(probe)
    if c.decode_obj(enc) != probe or _REAL_DATE_SHAPES.search(json.dumps(enc)) or enc["pct"] != 12.5 \
            or enc["cost"] == 1234.5:
        failures.append(f"secret codec: the date and money probe did not round trip: {enc}")
    # Tripwire for the boundary: a large number under a key not declared money and
    # not declared a quantity is probably money the list forgot.
    quantity_keys = {"planned_qty", "executed_qty", "remaining_qty", "rate_global", "rate_own",
                     "rate_planned", "rate_recent", "rate_required_late", "rate_required_trend",
                     "rate_contracted", "activity_days", "words"}
    folder = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "examples")
    if os.path.isdir(folder):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, os.path.join(HERE, "review.py"),
                            os.path.join(folder, "rodovia-ficticia-rev03.xml"),
                            os.path.join(folder, "rodovia-ficticia-rev04.xml"),
                            "--free", "--outdir", tmp, "--quiet"], check=True, capture_output=True)
            big = set()
            for name in os.listdir(tmp):
                obj = _payload_of(os.path.join(tmp, name)) if name.endswith(".html") \
                    else json.load(open(os.path.join(tmp, name), encoding="utf-8"))
                stack = [(None, obj)]
                while stack:
                    k, o = stack.pop()
                    if isinstance(o, dict):
                        stack.extend(o.items())
                    elif isinstance(o, list):
                        stack.extend((k, x) for x in o)
                    elif isinstance(o, (int, float)) and not isinstance(o, bool) and abs(o) >= 1e6 \
                            and k not in sc.LEGIBILITY["money_keys"] and k not in quantity_keys:
                        big.add(k)
            if big:
                failures.append(f"secret boundary: large numbers under keys not classified: {sorted(big)}")
    return failures


def guard_checks() -> list:
    """The Claude Code hook, fed the calls a session makes and the ones it must not."""
    import importlib.util

    import secret_mode
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "work", "run1")
        os.makedirs(work)
        secret_mode.write_guard(work)
        with open(os.path.join(work, "schedule-review.json"), "w") as fh:
            fh.write("{}")
        vault = os.path.join(tmp, "home", ".cronoaudit", "vault", "run1")
        os.makedirs(vault)
        original = os.path.join(tmp, "Contrato 999", "cronograma.xml")
        os.makedirs(os.path.dirname(original))
        open(original, "w").close()
        os.symlink(original, os.path.join(work, "link.xml")) if hasattr(os, "symlink") and os.name != "nt" else None
        hook = os.path.join(work, ".claude", "hooks", "cronoaudit_guard.py")
        spec = importlib.util.spec_from_file_location("cronoaudit_guard", hook)
        g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g)
        guard = g.load_guard()
        s = os.path.join(ROOT, "scripts").replace("\\", "/")
        py = sys.executable
        cases = [
            ("Read", {"file_path": os.path.join(vault, "back.json")}, False, "Read of a vault file"),
            ("Bash", {"command": f'cat "{original}"'}, False, "cat of the original"),
            ("Grep", {"pattern": "x", "path": vault}, False, "Grep in the vault"),
            ("Read", {"file_path": os.path.join(work, "schedule-review.json")}, True, "Read in the work folder"),
            ("Bash", {"command": "python3 -c \"print(open('/etc/hosts').read())\""}, False, "python -c"),
            ("Bash", {"command": "env"}, False, "env"),
            ("Bash", {"command": "printenv OLDPWD"}, False, "printenv"),
            ("Bash", {"command": "cd .."}, False, "cd .."),
            ("Bash", {"command": "cat schedule-review.json | python3"}, False, "pipe into an interpreter"),
            ("Bash", {"command": "cat $HOME/x"}, False, "a variable"),
            ("Bash", {"command": "ls ../"}, False, "ls of the parent"),
            ("Bash", {"command": f'"{py}" {s}/review.py "{original}" --free'}, False, "review.py on the original"),
            ("Bash", {"command": f"python3 {s}/secret_decode.py text"}, False, "secret_decode text"),
            ("Bash", {"command": f"python3 {s}/secret_decode.py finish"}, True, "secret_decode finish"),
            ("Bash", {"command": f'python3 {s}/inject_narrative.py schedule-review.html synthesis.txt '
                                 f'--who "Claude, via the skill"'}, True, "inject_narrative"),
            ("Bash", {"command": "head -50 schedule-review.json | grep -n x 2>&1"}, True, "reading pipeline"),
            ("Bash", {"command": "ls"}, True, "ls"),
            ("Write", {"file_path": os.path.join(work, "synthesis.txt")}, True, "Write the synthesis"),
            ("Write", {"file_path": os.path.join(work, ".claude", "settings.json")}, False, "Write the hook's settings"),
            ("Edit", {"file_path": original}, False, "Edit the original"),
            ("Glob", {"pattern": "/**/*.xml"}, False, "Glob from the root"),
            ("Glob", {"pattern": "*.json"}, True, "Glob in the work folder"),
            ("Read", {"file_path": os.path.join(ROOT, "SKILL.md")}, True, "Read the skill's text"),
            ("Read", {"file_path": os.path.join(ROOT, "templates", "report.custom.html")}, False,
             "Read a customised template"),
            ("Bash", {"command": "cat link.xml"}, os.name == "nt", "cat through a symlink to the original"),
            ("Bash", {"command": "echo x > ../out.txt"}, False, "redirect outside"),
            ("PowerShell", {"command": f'Get-Content "{original}"'}, False, "PowerShell reading the original"),
            ("PowerShell", {"command": "Get-ChildItem"}, False, "PowerShell even inside the folder"),
            ("Monitor", {"command": f"cat {original}"}, False, "Monitor running a command"),
            ("mcp__claude-in-chrome__navigate", {"url": "file:///" + original}, False, "an MCP tool"),
            ("ReadMcpResourceTool", {"uri": "file:///" + original}, False, "an MCP resource"),
            ("TaskCreate", {"subject": "x"}, True, "a tool that touches no file"),
            ("Skill", {"skill": "cronoaudit"}, True, "the Skill tool"),
            ("ToolSearch", {"query": "x"}, True, "ToolSearch"),
            ("Artifact", {"file_path": original, "asset": True}, False, "Artifact uploading the original"),
            ("SendUserFile", {"files": [original]}, False, "SendUserFile with the original"),
            ("SendMessage", {"to": "other", "message": "read the original"}, False,
             "SendMessage to a session that is not guarded"),
            ("Workflow", {"script": "x"}, False, "Workflow"),
            ("WebSearch", {"query": "x"}, False, "a tool outside the allowlist"),
            ("SomeFutureTool", {}, False, "a tool the guard has never heard of"),
        ]
        if os.name != "nt":
            cases.append(("Read", {"file_path": os.path.join(work, "link.xml")}, False,
                          "Read through a symlink to the original"))
        for tool, inp, want, label in cases:
            ok, _reason = g.decide(guard, {"tool_name": tool, "tool_input": inp, "cwd": work})
            if ok != want:
                failures.append(f"guard: {label} was {'allowed' if ok else 'blocked'}")
        # The hook as Claude Code runs it: exit 2 blocks, 0 allows, garbage blocks.
        for payload, code in ((json.dumps({"tool_name": "Read", "tool_input": {"file_path": original},
                                           "cwd": work}), 2),
                              (json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"},
                                           "cwd": work}), 0),
                              ("not json", 2)):
            r = subprocess.run([sys.executable, hook], input=payload, capture_output=True, text=True)
            if r.returncode != code:
                failures.append(f"guard: the hook process returned {r.returncode}, not {code}")
        settings = json.load(open(os.path.join(work, ".claude", "settings.json"), encoding="utf-8"))
        deny = settings["permissions"]["deny"]
        if not {"PowerShell", "Monitor"} <= set(deny) or \
                settings.get("env", {}).get("CLAUDE_CODE_USE_POWERSHELL_TOOL") != "0":
            failures.append(f"guard: settings.json does not deny PowerShell and Monitor: {settings}")
        if settings["hooks"]["PreToolUse"][0]["matcher"] != "*" or \
                settings.get("disableClaudeAiConnectors") is not True or \
                not {"Artifact", "SendUserFile", "SendMessage"} <= set(deny):
            failures.append("guard: the hook does not see every tool, or connectors and "
                            f"file-carrying tools are not closed: {settings}")
        if not any(d.startswith("Read(") and d.endswith("/**)") for d in deny) or \
                "PreToolUse" not in settings["hooks"]:
            failures.append(f"guard: settings.json lacks the deny rule or the hook: {settings}")
    return failures


def secret_checks() -> dict:
    """Round trip and leak test over the fixtures and the example, and the guard."""
    failures = secret_unit_checks() + guard_checks()
    sets = [[os.path.join(ROOT, "fixtures", n)] for n in ("positive.xml", "negative.xml", "bare.xml")]
    sets.append([os.path.join(ROOT, "fixtures", "cycle_prev.xml"), os.path.join(ROOT, "fixtures", "cycle_curr.xml")])
    folder = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "examples")
    if os.path.isdir(folder):
        ex = [os.path.join(folder, f"rodovia-ficticia-rev0{i}.xml") for i in (3, 4)]
        sets += [[ex[0]], [ex[1]], ex]
    # Surfaces no fixture carries: header fields, a note, a named holiday, a task
    # name with a date inside, a hyperlink. Built from the positive fixture.
    variant_dir = tempfile.mkdtemp()
    with open(os.path.join(ROOT, "fixtures", "positive.xml"), encoding="utf-8") as fh:
        x = fh.read()
    x = x.replace("<Title>Positive fixture</Title>",
                  "<Title>Positive fixture</Title><Subject>Contrato 4711 do Cliente Exemplar</Subject>"
                  "<Company>Construtora Exemplo Ltda</Company><Author>Fulano de Tal</Author>"
                  "<Manager>Beltrana Gerente</Manager><LastAuthor>Sicrano Revisor</LastAuthor>"
                  "<Keywords>lote sigiloso</Keywords>"
                  # A real value that is also a word cronoaudit writes in every work
                  # folder: the leak test must excuse it as program vocabulary.
                  "<Category>secret</Category>", 1)
    x = x.replace("<Name>Holiday</Name>", "<Name>Feriado Municipal de Exemplópolis</Name>", 1)
    x = x.replace("<Name>A1 successor started early</Name>",
                  "<Name>Marco 15/03/2027 — Ponte do Exemplo</Name>"
                  "<Notes>Ver ofício 22/2026 de 03/02/2026, valor R$ 1.234.567,89</Notes>"
                  "<Hyperlink>Pasta do Contrato</Hyperlink>", 1)
    variant = os.path.join(variant_dir, "Contrato-4711-cronograma.xml")
    with open(variant, "w", encoding="utf-8") as fh:
        fh.write(x)
    sets.append([variant])
    totals = {"runs": 0, "sidecars": 0, "reports": 0, "values_equal": 0}
    for files in sets:
        with tempfile.TemporaryDirectory() as tmp:
            r = secret_roundtrip(files, tmp)
        failures += [f"{'+'.join(os.path.basename(f) for f in files)}: {x}" for x in r["failures"]]
        if files == [variant] and not (r["stats"].get("excused") or {}).get("vocabulary"):
            failures.append("secret: a real value equal to a program word was not excused as vocabulary")
        totals["runs"] += 1
        for k in ("sidecars", "reports", "values_equal"):
            totals[k] += r["stats"][k]
    import shutil as _shutil
    _shutil.rmtree(variant_dir, ignore_errors=True)
    # A customised template is the organisation's branding: it must not reach the work folder.
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(ROOT, "templates", "report.html"), encoding="utf-8") as fh:
            tpl = fh.read().replace("<body>", "<body><!-- Marca Corporativa Sigilosa -->", 1)
        custom = os.path.join(tmp, "custom.html")
        with open(custom, "w", encoding="utf-8") as fh:
            fh.write(tpl)
        orig = os.path.join(tmp, "orig")
        os.makedirs(orig)
        _shutil.copyfile(os.path.join(ROOT, "fixtures", "positive.xml"), os.path.join(orig, "positive.xml"))
        subprocess.run([sys.executable, os.path.join(HERE, "review.py"), os.path.join(orig, "positive.xml"),
                        "--secret", "--quiet", "--template", custom, "--workdir", os.path.join(tmp, "work")],
                       check=True, capture_output=True, env=_secret_env(os.path.join(tmp, "cfg")),
                       stdin=subprocess.DEVNULL)
        if "Marca Corporativa" not in tpl:
            failures.append("secret: the custom-template probe was not built")
        for folder, _d, fnames in os.walk(os.path.join(tmp, "work")):
            for fname in fnames:
                with open(os.path.join(folder, fname), encoding="utf-8", errors="replace") as fh:
                    if "Marca Corporativa" in fh.read():
                        failures.append("secret leak: a customised template reached the work folder")
    # Same project, two separate runs: one key, the same tokens on both sides.
    if os.path.isdir(folder):
        import secret_codec
        with tempfile.TemporaryDirectory() as tmp:
            home = os.path.join(tmp, "cfg")
            orig = os.path.join(tmp, "orig")
            os.makedirs(orig)
            import shutil
            for f in ex:
                shutil.copyfile(f, os.path.join(orig, os.path.basename(f)))
            tables = []
            for f in ex:
                subprocess.run([sys.executable, os.path.join(HERE, "review.py"),
                                os.path.join(orig, os.path.basename(f)), "--secret", "--quiet",
                                "--workdir", os.path.join(tmp, "work")], check=True, capture_output=True,
                               env=_secret_env(home), stdin=subprocess.DEVNULL)
            for run_id in os.listdir(os.path.join(home, "vault")):
                if run_id != "keys":
                    with open(os.path.join(home, "vault", run_id, "back.json"), encoding="utf-8") as fh:
                        tables.append(json.load(fh))
            keys = os.listdir(os.path.join(home, "vault", "keys"))
            a, b = ({v: k for k, v in t["tokens"].items()} for t in tables)
            shared = set(a) & set(b)
            if len(keys) != 1 or not shared or any(a[x] != b[x] for x in shared) \
                    or tables[0]["origin"] != tables[1]["origin"] or tables[0]["k"] != tables[1]["k"]:
                failures.append("secret: two runs of the same project do not share key, tokens, origin and k")
    return {"failures": failures, "totals": totals}


def run_all() -> int:
    failures = []

    pos = analyse("positive.xml")
    for code in CODES:
        if pos["counts"][code]["distinct_activities"] < 1:
            failures.append(f"positive: {code} did not fire -- the probe is blind to it")

    # Both ends of a violated link must be marked, to agree with the tool's own count.
    for code in ("A1", "A2"):
        c = pos["counts"][code]
        if c["as_successors"] < 1 or c["as_predecessors"] < 1:
            failures.append(f"positive: {code} marked only one end of the link")

    neg = analyse("negative.xml")
    for code in CODES:
        got = neg["counts"][code]["distinct_activities"]
        if got:
            failures.append(f"negative: {code} fired {got} times on a consistent schedule")

    # The transversal rule: a predecessor that is only pending a record (P) is a
    # reporting defect, not a network breach. UID 11 is in P and precedes UID 12,
    # which has started -- that must NOT appear as A1.
    a1_uids = {f["uid"] for f in pos["findings"]["A1"]}
    if 11 in a1_uids or 12 in a1_uids:
        failures.append(
            "positive: the P migration rule regressed -- a pending record was "
            "counted as a network breach, which accuses execution for a "
            "record-keeping problem"
        )

    if not pos["findings"]["P"]:
        failures.append("positive: P did not fire, so the migration rule was never exercised")

    # ---- the comparator, on the cycle pair.
    cyc = compare_cycle()
    readings = {t["reading"] for t in cyc["trend"]}
    if "execution" not in readings:
        failures.append("cycle: no movement was read as execution")
    if "replan" not in readings:
        failures.append("cycle: no movement was read as replan")
    if not cyc["baseline_moved"]:
        failures.append("cycle: a rebased baseline was not detected")
    if not cyc["warnings"]:
        failures.append("cycle: a rebased baseline and a scope change raised no warning")
    if not cyc["unmatched"]["inserted"] or not cyc["unmatched"]["removed"]:
        failures.append("cycle: inserted or removed activities were not detected")
    # The residue must be named, not silently absorbed: scope changed the denominator,
    # so the headline movement is NOT all progress and the report must say so.
    if cyc["movement_unexplained_points"] in (None, 0):
        failures.append(
            "cycle: the unexplained residue was not computed, so a movement that is "
            "partly scope change would be reported as progress"
        )
    aggregates_note = cyc["conventions"]["aggregates"]
    if "called twice" not in aggregates_note:
        failures.append("cycle: the shared-reference convention is no longer declared")

    # ---- what changed in the model itself: one positive case per finding.
    def ids(rows):
        return sorted(r["id"] for r in rows)

    pf = cyc["project_finish"]
    if pf["delta_days"] != 14.0 or pf["delta_unit"] != "calendar days":
        failures.append(f"cycle finish: the project finish moved 14 calendar days, read {pf['delta_days']}")
    if (pf["current"]["end"] or {}).get("id") != 8 or (pf["current"]["driver"] or {}).get("id") != 7:
        failures.append("cycle finish: the closing milestone (8) and its driving activity (7) were not named")
    if [n["id"] for n in pf["current"]["chain"]][:2] != [8, 7]:
        failures.append("cycle finish: the driving chain does not run from the milestone to its driver")
    if pf["driver_changed"] is not False or "approximated" not in pf["current"]["driver_basis"]:
        failures.append("cycle finish: the driver comparison or its declared approximation is missing")
    cp = cyc["critical_path"]
    if ids(cp["entered"]) != [9] or ids(cp["left"]) != [10]:
        failures.append(f"cycle critical: entered {ids(cp['entered'])} / left {ids(cp['left'])}, expected [9] / [10]")
    if cp["criterion_current"] != "flag":
        failures.append("cycle critical: the file carries the Critical flag and it was not the criterion")
    if [r["id"] for r in cp["float_fell_top"]] != [11, 9] or cp["float_fell_top"][0]["float_fell_days"] != 15.0:
        failures.append("cycle critical: the float ranking is not 11 (15 days) then 9 (10 days)")
    if any(r["id"] == 10 for r in cp["float_fell_top"]):
        failures.append("cycle critical: an activity that GAINED float is listed as having lost it")
    lg = cyc["logic"]
    got = {k: [(r["id"], r["predecessor_id"]) for r in lg[k]]
           for k in ("links_added", "links_removed", "lag_changed", "type_changed")}
    want = {"links_added": [(12, 11)], "links_removed": [(13, 11)],
            "lag_changed": [(12, 9)], "type_changed": [(12, 10)]}
    if got != want:
        failures.append(f"cycle logic: link changes read as {got}")
    else:
        lag = lg["lag_changed"][0]
        if (lag["lag_before"]["value"], lag["lag_after"]["value"]) != (2.0, 5.0):
            failures.append("cycle logic: the lag did not read 2 then 5 working days")
        tc = lg["type_changed"][0]
        if (tc["type_before"], tc["type_after"]) != ("FS", "SS"):
            failures.append("cycle logic: the link type did not read FS then SS")
    if ids(lg["constraints_added"]) != [13] or ids(lg["constraints_changed"]) != [14] or lg["constraints_removed"]:
        failures.append("cycle logic: constraint added on 13 / changed on 14 not read")
    else:
        ch = lg["constraints_changed"][0]
        if (ch["type_before"], ch["type_after"]) != ("SNET", "MSO") or ch["date_before"] == ch["date_after"]:
            failures.append("cycle logic: the hardened constraint lost its type or its date")
    # The untouched link 12 <- 7 must appear nowhere: the negative control.
    if any((r["id"], r["predecessor_id"]) == (12, 7) for k in want for r in lg[k]):
        failures.append("cycle logic: an unchanged link was reported as edited")
    du = cyc["duration_changed"]
    if ids(du) != [7] or du[0]["delta_days"] != 10.0:
        failures.append(f"cycle duration: expected only activity 7, +10 working days; got {du}")
    # 16 and 17 changed duration too, but they had started: that is execution.
    pr = cyc["past_rewritten"]
    if ids(pr["actual_start"]) != [15] or ids(pr["actual_finish"]) != [16, 17]:
        failures.append("cycle past: rewritten actual start (15) or finish (16, 17) not detected")
    if ids(pr["percent_decreased"]) != [15, 17] or pr["activities"] != 3:
        failures.append("cycle past: a percent that went down was missed, or counted twice")
    if pr["actual_removed"] != 1:
        failures.append("cycle past: a withdrawn actual finish was not told apart from a changed one")
    if any(r["id"] == 2 for k in ("actual_start", "actual_finish", "percent_decreased") for r in pr[k]):
        failures.append("cycle past: honest progress was accused of rewriting the past")
    if not any(w["code"] == "past_rewritten" for w in cyc["warning_codes"]):
        failures.append("cycle past: the rewritten past raised no warning")
    q = {m["code"]: m for m in cyc["quality"]["metrics"]}
    if len(q) != 14:
        failures.append("cycle quality: the fourteen metrics are not side by side")
    elif q["Q5"]["previous"]["count"] != 0 or q["Q5"]["current"]["count"] != 1 \
            or q["Q5"]["change"] != "worsened" or q["Q5"]["crossed"] != "pass->fail":
        failures.append("cycle quality: the hard constraint added this cycle did not move Q5")
    import network_quality as nq_mod
    import parse_mspdi as pm_mod
    curr_q = nq_mod.build(pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml")))
    for m in curr_q["metrics"]:
        if m["code"] != "Q10" and q[m["code"]]["current"]["count"] != m["count"]:
            failures.append(f"cycle quality: {m['code']} differs from the review's own figure")
    # The float criterion, when the file carries no Critical flag at all.
    import compare_snapshots as cs_mod
    import copy as copy_mod
    bare = []
    for name in ("cycle_prev.xml", "cycle_curr.xml"):
        mdl = copy_mod.deepcopy(pm_mod.parse(os.path.join(ROOT, "fixtures", name)))
        for t in mdl["tasks"]:
            t["critical"] = None
        bare.append(mdl)
    cp2 = cs_mod.compare(*bare)["critical_path"]
    if cp2["criterion_current"] != "float" or ids(cp2["entered"]) != [9] or ids(cp2["left"]) != [10]:
        failures.append("cycle critical: without the flag, total float at or below zero was not used")
    # Comparing a file with itself must find nothing: the silent half.
    same = pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    quiet = cs_mod.compare(same, copy_mod.deepcopy(same))
    noise = (quiet["critical_path"]["entered"] + quiet["critical_path"]["left"]
             + quiet["critical_path"]["float_fell_top"] + quiet["duration_changed"]
             + [r for k in ("links_added", "links_removed", "lag_changed", "type_changed",
                            "constraints_added", "constraints_changed", "constraints_removed")
                for r in quiet["logic"][k]])
    if noise or quiet["past_rewritten"]["activities"] or quiet["project_finish"]["delta_days"] != 0 \
            or any(m["change"] not in (None, "unchanged") for m in quiet["quality"]["metrics"]):
        failures.append("cycle: a file compared with itself produced findings")
    for key in ("movement_points", "decomposition_sums_to_points", "movement_unexplained_points",
                "residual_remainder_points"):
        if str(quiet[key]).startswith("-"):
            failures.append(f"cycle: {key} is a negative zero")
    # No path leaves the engine, and both languages carry every cycle string.
    if os.sep in (cyc["previous"]["source"] or "") or os.sep in (pm_mod.parse(
            os.path.join(ROOT, "fixtures", "positive.xml"))["source"]):
        failures.append("privacy: a source field carries a path instead of a file name")
    import i18n as i18n_mod
    import narrative as nar_mod
    import report_data as rd_mod
    for table, label in ((i18n_mod.CYCLE, "cycle strings"), (nar_mod.RC, "cycle readings"),
                         (nar_mod.R, "readings"),
                         (i18n_mod.CONSTRAINTS, "constraint names")):
        for lang in table:
            gap = set(table["en"]) ^ set(table[lang])
            if gap:
                failures.append(f"language: {label} differ between en and {lang}: {sorted(gap)}")
    for lang in ("en", "pt"):
        pay = rd_mod.build_cycle(cyc, lang=lang)
        if [s["code"] for s in pay["sections"]] != ["C1", "C5", "C3", "C4", "C2", "C6"]:
            failures.append(f"cycle report ({lang}): the six sections are not all present, in order")
        for s in pay["sections"]:
            if not s["reading"] or not s["criterion"] or not s["reproduce"]:
                failures.append(f"cycle report ({lang}): {s['code']} lacks its reading or its filter")
        sev = {s["code"]: s["severity"] for s in pay["sections"]}
        if sev.get("C5") != "critical":
            failures.append(f"cycle report ({lang}): a rewritten past is not the critical finding")
        if pay["meta"]["baseline_label"] is None or "1" not in pay["meta"]["baseline_label"]:
            failures.append(f"cycle report ({lang}): baseline 1 is not named in plain words")
    if rd_mod.baseline_label("0", i18n_mod.cycle_text("pt")) is not None:
        failures.append("cycle report: baseline slot 0 is shown, and it says nothing")
    quiet_pay = rd_mod.build_cycle(quiet, lang="pt")
    if not all(s["empty"] for s in quiet_pay["sections"] if s["code"] in ("C2", "C3", "C4", "C5")):
        failures.append("cycle report: a section with nothing to show is not collapsed to one line")

    # ---- the residue in named terms (0.7.2). The fixture's residue comes from the
    # BAC shrinking (7,000 removed at 0%, 5,000 inserted); then the removed row is
    # given 100% and its erased earned value must appear as its own term, in C5,
    # and in both languages -- the agent had to infer it on a real run.
    import narrative as nar_mod2
    terms = cyc["residual_terms"]
    if terms is None or abs(cyc["residual_remainder_points"]) >= 0.01 \
            or abs(terms["bac_change"]["points"] - cyc["movement_unexplained_points"]) >= 0.01 \
            or terms["bac_change"]["bac_delta"] != -2000.0:
        failures.append(f"residual terms: the fixture's residue is not the BAC change, exactly: {terms}")
    if any(abs(quiet["residual_terms"][k]["points"]) for k in cs_mod.TERM_KEYS):
        failures.append("residual terms: a file compared with itself carries a residue term")
    pv = copy_mod.deepcopy(pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_prev.xml")))
    cv = pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    for t in pv["tasks"]:
        if t["uid"] == 6:
            t["physical_percent_complete"] = 100.0
            t["percent_complete"] = 100.0
    gone = cs_mod.compare(pv, cv)
    gt = gone["residual_terms"]
    want_rem = round(-7000.0 / gone["previous"]["budget_at_completion"] * 100, 4)
    if abs(gt["removed_earned"]["points"] - want_rem) > 1e-4 or abs(gone["residual_remainder_points"]) >= 0.01:
        failures.append(f"residual terms: the removed row's erased earned value is not its own term "
                        f"({gt['removed_earned']['points']} vs {want_rem}, remainder "
                        f"{gone['residual_remainder_points']})")
    gpr = gone["past_rewritten"]
    if [r["id"] for r in gpr["removed_with_progress"]] != [6] or gpr["activities"] != pr["activities"] + 1 \
            or gpr["removed_with_progress"][0]["earned_erased"] != 7000.0:
        failures.append(f"cycle past: a removed activity at 100% is not counted as rewritten past: {gpr}")
    for lang, words in (("en", ("row 6 of the previous delivery", "removed from the schedule")),
                        ("pt", ("linha 6 da entrega anterior", "removida do cronograma"))):
        rd_ = nar_mod2.build_cycle(gone, lang, rd_mod.fmt_date)
        mv_ = " ".join(rd_.get("movement", []))
        c5_ = " ".join(rd_.get("c5", []))
        if words[0] not in mv_ or words[1] not in c5_:
            failures.append(f"residual reading ({lang}): the erased earned value is not named: {mv_} / {c5_}")
        if re.search(r"-\d[\d,.]* (?:are not explained|não são explicados)", mv_):
            failures.append(f"residual reading ({lang}): a negative residue is read as a count: {mv_}")
        pay_ = rd_mod.build_cycle(gone, lang=lang)
        c5s = next(s_ for s_ in pay_["sections"] if s_["code"] == "C5")
        if not any(l_["rows"] and l_["rows"][0].get("ev") == 7000.0 for l_ in c5s["lists"]):
            failures.append(f"cycle report ({lang}): C5 does not list the removed row with its earned value")
        if not any(w_["text"].count("6") and ("has a name" in w_["text"] or "tem nome" in w_["text"])
                   for w_ in pay_["warnings"]):
            failures.append(f"cycle report ({lang}): the residue warning does not name its terms")
    # A positive residue keeps the plain sentence, and names the BAC term.
    mv_en = " ".join(nar_mod2.build_cycle(cyc, "en", rd_mod.fmt_date).get("movement", []))
    if "are not explained by work done" not in mv_en or "budget at completion" not in mv_en:
        failures.append(f"residual reading: the BAC term of a positive residue is not named: {mv_en}")

    # ---- the network rules the in-tool implementation taught, each with a control.
    a1_pairs = {(p["successor_id"], p["predecessor_id"]) for p in pos["pairs"]["A1"]}
    if (15, 14) in a1_pairs:
        failures.append("network: an overlap covered by a lead was accused as A1 -- lag not honoured")
    if (17, 16) in a1_pairs:
        failures.append("network: a pair with both activities complete was counted, against the rule")
    ign = pos.get("ignored", {}).get("A1_both_complete", [])
    if not any(x["successor_id"] == 17 and x["predecessor_id"] == 16 for x in ign):
        failures.append("network: the both-complete inverted pair was not recorded as ignored")
    if (19, 18) not in a1_pairs:
        failures.append("network: a start-to-start lag violation was not detected")
    if (2, 1) not in a1_pairs:
        failures.append("network: the plain finish-to-start breach stopped firing")
    lt = pos["conventions"].get("link_types_evaluated", {})
    if lt.get("SS", 0) < 1:
        failures.append("network: start-to-start links were not counted as evaluated")
    h_why = {f["uid"]: f.get("why") for f in pos["findings"]["H"]}
    if 20 not in h_why or not str(h_why[20]).startswith("start"):
        failures.append("H: a start elapsed with no actual start was not flagged by the start rule")
    if pos["conventions"].get("threshold_basis") != "working_days_task_calendar":
        failures.append("threshold: E and C must be measured in working days of the task calendar")

    # ---- calendars. Leaving them out does not approximate the answer, it invents
    # one: a real programme had 107 calendars, most tasks on a 9-hour six-day week
    # while the header said 8 hours over five days.
    import parse_mspdi
    pm = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "positive.xml"))
    cal_block = pm.get("calendars") or {}
    if cal_block.get("count", 0) < 2:
        failures.append("calendars: the fixture's calendars were not parsed")
    in_use = {c["name"]: c for c in cal_block.get("in_use", [])}
    six = in_use.get("Earthworks six-day")
    if not six:
        failures.append("calendars: the six-day calendar is not reported as in use")
    else:
        if six["hours_per_day"] != 9.0:
            failures.append(
                f"calendars: six-day calendar day length read as {six['hours_per_day']}h, "
                "not 9h -- durations on it will convert wrongly"
            )
        if six["working_days_per_week"] != 6:
            failures.append("calendars: the six-day working week was not detected")
        if six["non_working_exceptions"] < 1:
            failures.append("calendars: the holiday exception was not detected")
    # UID 13 sits on the six-day calendar and its duration matches the real working
    # time once the holiday is removed. If it is flagged, the calendar is being
    # ignored -- this is the negative control for the whole calendar path.
    g_uids = {f["uid"] for f in pos["findings"]["G"]}
    if 13 in g_uids:
        failures.append(
            "calendars: a consistent activity on a six-day calendar with a holiday was "
            "flagged as G, so the calendar is not being applied"
        )
    if 8 not in g_uids:
        failures.append("calendars: the genuinely inconsistent duration stopped firing")

    # ---- language. The report follows the schedule, not a flag: the person running
    # the review is often not the person who wrote the file.
    import i18n
    pt_model = {
        "project": {"title": "Duplicação de pista"},
        "calendars": {"in_use": [{"name": "Terraplenagem"}, {"name": "Obras civis"}]},
        "tasks": [
            {"name": "Execução de terraplenagem no trecho sul"},
            {"name": "Implantação de drenagem profunda"},
            {"name": "Concreto para as obras de arte especiais"},
            {"name": "Sinalização horizontal e vertical da faixa"},
        ],
    }
    en_model = {
        "project": {"title": "Highway widening"},
        "calendars": {"in_use": [{"name": "Earthworks"}]},
        "tasks": [
            {"name": "Execution of the earthworks on the southern section"},
            {"name": "Installation of the deep drainage system"},
            {"name": "Concrete for the bridges and structures"},
            {"name": "Signage and lane marking for the works"},
        ],
    }
    got_pt = i18n.detect(pt_model)
    got_en = i18n.detect(en_model)
    if got_pt["lang"] != "pt":
        failures.append(f"language: Portuguese schedule detected as {got_pt['lang']}")
    if got_en["lang"] != "en":
        failures.append(f"language: English schedule detected as {got_en['lang']}")
    thin = i18n.detect({"project": {}, "tasks": [{"name": "X"}]})
    if thin["confidence"] != "low":
        failures.append(
            "language: a file with almost no text did not report low confidence, so a "
            "guess from noise would look like a decision"
        )
    # Every interface string must exist in both languages, or a report silently
    # falls back to English mid-page.
    en_ui = i18n.UI["en"]
    for lang in i18n.UI:
        missing = [k for k in en_ui if k not in i18n.UI[lang]]
        if missing:
            failures.append(f"language: {lang} is missing {len(missing)} labels: {missing[:5]}")
    for lang in i18n.FINDINGS:
        for code in CODES:
            entry = i18n.FINDINGS[lang].get(code)
            if not entry or len(entry) != 5:
                failures.append(f"language: {lang} has no complete text for finding {code}")

    # ---- custom field discovery. An organisation keeps its meaning in these, and
    # the point is to show someone candidates rather than ask them to recall.
    import custom_fields as cf_mod
    import report_data
    disc = (pm.get("custom_fields") or {})
    if disc.get("declared", 0) < 3:
        failures.append("fields: the fixture's custom field definitions were not read")
    by_alias = {f.get("alias"): f for f in disc.get("fields", [])}
    d_field = by_alias.get("DISCIPLINA")
    if not d_field:
        failures.append("fields: DISCIPLINA was not discovered")
    else:
        if d_field["type"] != "text":
            failures.append(f"fields: DISCIPLINA typed as {d_field['type']} from its values")
        if not d_field["closed_set"]:
            failures.append("fields: a three-value field was not recognised as a closed set")
        if "discipline" not in d_field["suggested_roles"]:
            failures.append("fields: DISCIPLINA did not suggest the discipline role")
    q_field = by_alias.get("QTDE")
    if q_field and q_field["type"] != "number":
        failures.append(f"fields: QTDE typed as {q_field['type']}, not number")

    cands, sparse = cf_mod.interview_candidates(disc)
    if "discipline" not in cands:
        failures.append("fields: no discipline candidate offered for the interview")
    # A justification field filled on almost nothing must surface as a finding, not
    # be silently dropped below a threshold.
    if "justification" not in sparse:
        failures.append(
            "fields: a barely-populated justification field was dropped instead of being "
            "reported as the finding it is"
        )

    # Grouping by a discovered field, by alias, must actually bucket the work.
    res_pos = analyse_raw(pm)
    by_wbs = report_data.build_review(pm, res_pos, grouping="wbs")
    by_disc = report_data.build_review(pm, res_pos, grouping="DISCIPLINA")
    missing_grp = report_data.build_review(pm, res_pos, grouping="NO_SUCH_FIELD")
    if by_disc["meta"]["grouping_mode"] != "custom":
        failures.append("fields: grouping by alias did not resolve to the custom field")
    if len(by_disc["charts"]["by_group"]) < 3:
        failures.append("fields: grouping by discipline produced fewer buckets than values")
    if missing_grp["meta"]["grouping_mode"] != "missing":
        failures.append(
            "fields: a grouping field that does not exist was not reported as missing, so "
            "everything would silently land in one bucket"
        )
    if not by_wbs["meta"].get("grouping_uninformative") and len(by_wbs["charts"]["by_group"]) < 2:
        failures.append("fields: a single-bucket grouping was not flagged as uninformative")

    # ---- earned value reconciled against the file's own figures.
    rc = by_wbs["meta"]["reconciliation"]
    if rc["leaves_compared"] < 5:
        failures.append("reconciliation: the file's BCWP was not read")
    if rc["ahead_of_baseline"] < 1:
        failures.append(
            "reconciliation: work done ahead of its baseline window, which the tool credits "
            "nothing for until the status date reaches the window, was not classified -- it "
            "would surface as an unexplained mismatch or, worse, be hidden"
        )
    if rc["unexplained"] != 0:
        failures.append(f"reconciliation: {rc['unexplained']} unexplained mismatches on a fixture "
                        "built to match to the cent")
    if rc["ev_method"] != "physical":
        failures.append("reconciliation: the declared earned value method was not read")
    # Slot election by coverage: the fixture keeps everything in slot 1, so 1 wins.
    if pm["prevailing_baseline"]["slot"] != "1":
        failures.append("baseline: coverage election picked the wrong slot on the fixture")

    # ---- the S-curve from the file's own phasing. Nothing invented: the per-task
    # sums must equal the totals the file writes, and a non-working day's sentinel
    # must never reach the curve.
    import phasing as phasing_mod
    curve = phasing_mod.build(os.path.join(ROOT, "fixtures", "positive.xml"), None)
    rr = curve["reconciliation"]
    if rr["phasing_sum_equals_cost"] != rr["with_cost"]:
        failures.append(
            f"phasing: baseline-cost blocks sum to the baseline cost on only "
            f"{rr['phasing_sum_equals_cost']} of {rr['with_cost']} tasks"
        )
    # Counted over the tasks where there is something to compare: zero against
    # zero is not agreement, so it is in neither the numerator nor the denominator.
    if rr["phasing_to_status_equals_bcws"] != rr["bcws_comparable"] or not rr["bcws_comparable"]:
        failures.append(
            f"phasing: blocks up to the status date equal the file's BCWS on only "
            f"{rr['phasing_to_status_equals_bcws']} of {rr['bcws_comparable']} comparable tasks"
        )
    if rr["bcws_comparable"] >= rr["tasks"]:
        failures.append("phasing: tasks with zero planned on both sides were counted as agreeing")
    T = curve["totals"]
    if T["earned_pct"] is None or T["planned_pct"] is None:
        failures.append("phasing: totals missing")
    # Earned to date must equal the sum of cost x physical over the leaves, which is
    # only true if the 32768 sentinel days were dropped before summing.
    expected = sum(
        ((t.get("baselines") or {}).get("1") or {}).get("cost", 0) * (t.get("physical_percent_complete") or 0) / 100
        for t in pm["tasks"] if not t.get("summary") and t.get("physical_percent_complete")
    )
    if abs(T["earned_to_date"] - expected) > 1.0:
        failures.append(
            f"phasing: earned to date {T['earned_to_date']} != cost x physical {expected:.2f}; "
            "a sentinel day leaked into the curve or the spread was not normalised"
        )
    if T["method_gap_points"] is None:
        failures.append("phasing: the other method's curve was not computed as sensitivity")
    if curve["method"] != "physical":
        failures.append("phasing: the declared earned value method was not read")
    if not curve["periods"] or curve["periods"][-1]["planned_cum_pct"] is None:
        failures.append("phasing: the monthly series is empty or lacks cumulative percent")
    if any(p["earned_cum"] is not None for p in curve["periods"] if p["period"] > "2026-06"):
        failures.append("phasing: earned values appear after the status month")

    # ---- money scale. MSPDI writes money in hundredths of the currency unit
    # (measured 22/11/2026 in MS Project 16: the XML value / 100 is what Project
    # shows). The fixture is written that way, so the model must read 10,000.00
    # where the file says 1000000.00. And the conversion must move absolute money
    # only: every ratio -- SPI, percents, weights, reconciliation counts -- has to be
    # identical to what the unscaled reading gave, to the last digit.
    bl_costs = sorted({((t.get("baselines") or {}).get("1") or {}).get("cost")
                       for t in pm["tasks"] if (t.get("baselines") or {}).get("1")} - {None})
    if 10000.0 not in bl_costs or max(bl_costs) >= 1e6:
        failures.append(f"money: baseline cost not read in currency units (hundredths not divided): "
                        f"{bl_costs[:4]}")
    import parse_mspdi as money_pm
    pos_xml = os.path.join(ROOT, "fixtures", "positive.xml")

    def money_run(scale):
        saved = money_pm.MONEY_SCALE
        money_pm.MONEY_SCALE = scale
        try:
            mdl = money_pm.parse(pos_xml)
            crv = phasing_mod.build(pos_xml, None)
            pay = report_data.build_review(mdl, analyse_raw(mdl), grouping="DISCIPLINA",
                                           lang="en", phasing=crv)
        finally:
            money_pm.MONEY_SCALE = saved
        return mdl, crv, pay

    m_raw, c_raw, p_raw = money_run(1)       # the reading before 22/11/2026
    m_cur, c_cur, p_cur = money_run(100)     # currency units

    def ratios(crv, pay):
        tt = crv["totals"]
        return {
            "totals": {k: tt[k] for k in ("planned_pct", "earned_pct", "earned_alt_pct", "spi",
                                          "method_gap_points")},
            "phasing_counts": {k: v for k, v in crv["reconciliation"].items()
                               if isinstance(v, (int, float)) and not isinstance(v, bool)},
            "periods": [(p["period"], p["planned_cum_pct"], p["earned_cum_pct"],
                         p["earned_alt_cum_pct"], p["spi_cum"]) for p in crv["periods"]],
            "review_counts": {k: v for k, v in pay["meta"]["reconciliation"].items()
                              if isinstance(v, int) and not isinstance(v, bool)},
            "groups": [(g.get("label"), g.get("weight_pct"), g.get("planned_pct"), g.get("earned_pct"))
                       for g in pay["charts"]["by_group"]],
        }

    r_raw, r_cur = ratios(c_raw, p_raw), ratios(c_cur, p_cur)
    for k in r_raw:
        if r_raw[k] != r_cur[k]:
            failures.append(f"money: converting the scale changed a ratio ({k}): {r_raw[k]} != {r_cur[k]}")
    for k in ("bac", ):
        a, b = c_raw[k], c_cur[k]
        if abs(a / 100 - b) > 0.005 + 1e-9:
            failures.append(f"money: {k} {b} is not the unscaled {a} / 100")
    for k in ("planned_to_date", "earned_to_date", "sv"):
        a, b = c_raw["totals"][k], c_cur["totals"][k]
        if (a is None) != (b is None) or (a is not None and abs(a / 100 - b) > 0.005 + 1e-9):
            failures.append(f"money: totals.{k} {b} is not the unscaled {a} / 100")
    for t_raw, t_cur in zip(m_raw["tasks"], m_cur["tasks"]):
        for k in ("bcws", "bcwp", "acwp", "cost", "fixed_cost"):
            a, b = t_raw[k], t_cur[k]
            if (a is None) != (b is None) or (a is not None and abs(a / 100 - b) > 1e-9 * max(1.0, abs(b))):
                failures.append(f"money: task {t_cur['uid']} {k} {b} is not the raw {a} / 100")
                break

    # ---- productivity from the file's own assignments. Quantities are hours of
    # an ISO duration; three rates; four dates; three verdicts.
    import resources as resources_mod
    prod = resources_mod.build(os.path.join(ROOT, "fixtures", "positive.xml"), pm)
    by_res = {r["name"]: r for r in prod["resources"]}
    cut = by_res.get("Earthworks cut")
    if not cut:
        failures.append("productivity: the material resource was not read")
    else:
        if abs(cut["planned_qty"] - 3500.0) > 0.01:
            failures.append(f"productivity: planned quantity {cut['planned_qty']} != 3500 -- the "
                            "hours-of-duration encoding was misread")
        if abs(cut["executed_qty"] - 1200.0) > 0.01:
            failures.append(f"productivity: executed quantity {cut['executed_qty']} != 1200")
        if not cut["rate_global"] or not (50 < cut["rate_global"] < 200):
            failures.append(f"productivity: global rate {cut['rate_global']} not between the two "
                            "activities' own rates")
    acts = {a["id"]: a for a in prod["activities"]}
    a22 = acts.get(22)
    if not a22:
        failures.append("productivity: the in-progress activity was not projected")
    else:
        # 400 executed over the working days ELAPSED since the actual start (17 to
        # 30 June on a five-day week: ten days, two of them without production), so
        # 40 a day, not the 50 a day the daily blocks show on the days work happened.
        # The practised rate includes the days nothing came out; that is the point.
        if not a22["rate_own"] or abs(a22["rate_own"] - 40.0) > 0.5:
            failures.append(f"productivity: own rate {a22['rate_own']} != 40 per working day")
        if a22["executed_source"] != "actual":
            failures.append("productivity: an entered quantity was labelled as inferred")
        if not a22["projected_own"] or not a22["verdict_own"]:
            failures.append("productivity: no projection or verdict on the in-progress activity")
        if not a22["finish_late"] or not a22["finish_baseline"]:
            failures.append("productivity: the four dates are incomplete")
        # 800 m3 left at 40 a day is 20 working days from 30/06, landing late July.
        # Trend is 03/07 and baseline 30/06, both passed; the late finish is
        # 03/07 plus 28 calendar days, 31/07, not yet passed. So: the baseline is
        # missed and the float absorbs it -- with a few days of float to spare.
        if a22["verdict_own"] != "baseline_delay":
            failures.append(f"productivity: own-rate verdict {a22['verdict_own']}, expected "
                            "baseline_delay")
        if a22.get("days_of_float_left_global") is None:
            failures.append("productivity: days of float left were not computed")
    a24 = acts.get(24)
    if not a24 or a24["executed_source"] != "inferred":
        failures.append("productivity: executed quantity derived from percent was not flagged inferred")
    if prod["summary"]["assignments_unassigned"] < 1:
        failures.append("productivity: the unassigned (-1) assignment was not counted")

    # ---- network quality: the fourteen metrics as an implementation, each with a
    # control in the fixture, and honesty about what a file cannot answer.
    import network_quality as quality_mod
    qres = quality_mod.build(pm, os.path.join(ROOT, "fixtures", "positive.xml"))
    qm = {m["code"]: m for m in qres["metrics"]}
    if qm["Q1"]["count"] < 1:
        failures.append("quality: open ends were not counted")
    if not any(i["id"] == 15 for i in qm["Q2"]["items"]):
        failures.append("quality: the lead on link 14->15 was not counted as Q2")
    if not any(i["id"] == 27 for i in qm["Q3"]["items"]):
        failures.append("quality: the 3-day lag on link 26->27 was not counted as Q3")
    if not any(i["id"] == 19 for i in qm["Q4"]["items"]):
        failures.append("quality: the start-to-start link was not counted as a non-FS type")
    if not any(i["id"] == 26 for i in qm["Q5"]["items"]):
        failures.append("quality: the must-finish-on constraint was not counted as hard")
    if qm["Q7"]["count"] != 0:
        failures.append("quality: negative float reported where the fixture has none")
    if qm["Q9"]["count"] != 0:
        failures.append("quality: actual dates after the status date reported where there are none")
    if not any(i["id"] == 25 for i in qm["Q10"]["items"]):
        failures.append("quality: an activity with duration and no resource was not counted as Q10")
    if qm["Q11"]["population"] < 1 or qm["Q11"]["count"] < 1:
        failures.append("quality: missed activities (due by status, not finished on time) not counted")
    if qm["Q12"]["population"] != 0:
        failures.append("quality: Q12 was computed from a file, which it cannot be")
    if qm["Q13"]["population"] != 0 and not qres["indices"]["cpli_meaningful"]:
        failures.append("quality: Q13 was computed without a deadline on the finish milestone")
    I = qres["indices"]
    if I["bei"] is None or not (0 <= I["bei"] <= 1):
        failures.append("quality: the baseline execution index was not computed")
    if I["cpli_meaningful"]:
        failures.append("quality: CPLI reported as meaningful with no deadline on the finish milestone")
    # With a deadline on the finish milestone, Q13 is a real index: the room to the
    # deadline is the float, and the table carries the same figure as the tile.
    # Found by an agent in secret mode on 22/11/2026: tile 1.0, table "not computable".
    import copy as _copy
    from datetime import timedelta as _td
    pm_dl = _copy.deepcopy(pm)
    _ms = sorted((t for t in pm_dl["tasks"] if t.get("milestone") and t.get("finish")
                  and not t.get("summary")), key=lambda t: t["finish"], reverse=True)
    if _ms:
        from datetime import datetime as _dtm
        _ms[0]["deadline"] = (_dtm.fromisoformat(_ms[0]["finish"]) + _td(days=9)).isoformat()
        pm_dl["project"]["finish"] = pm_dl["project"].get("finish") or _ms[0]["finish"]
        q_dl = quality_mod.build(pm_dl, os.path.join(ROOT, "fixtures", "positive.xml"))
        q13 = {m["code"]: m for m in q_dl["metrics"]}["Q13"]
        I_dl = q_dl["indices"]
        if not I_dl["cpli_meaningful"] or I_dl["cpli"] is None or I_dl["cpli"] <= 1:
            failures.append(f"quality: a deadline 9 days after the finish milestone left CPLI at {I_dl['cpli']}")
        elif q13["population"] != 1 or q13["status"] not in ("pass", "fail") \
                or abs(q13["share_pct"] - I_dl["cpli"] * 100) > 0.01:
            failures.append("quality: with a deadline, the Q13 row does not carry the tile's CPLI")
    if qres["qualitative"]["summaries_with_links_count"] < 1:
        failures.append("quality: a summary task carrying a link was not flagged")
    for mtr in qres["metrics"]:
        if mtr["threshold_pct"] is not None and mtr["population"] and mtr["status"] not in ("pass", "fail"):
            failures.append(f"quality: {mtr['code']} has a threshold and a population but no status")

    # ---- looking forward. Earned Schedule from the phased curve, with its limits;
    # look-ahead windows; rates by group; milestone bands; rain exposure.
    import forecast as forecast_mod
    fc = forecast_mod.build(pm, curve, prod, None)
    E = fc["earned_schedule"]
    if not E.get("available"):
        failures.append(f"forecast: earned schedule not available: {E.get('reason')}")
    else:
        for k in ("es_date", "spi_t", "ieac_t_date", "tspi", "sv_t_days", "planned_finish"):
            if E.get(k) is None:
                failures.append(f"forecast: earned schedule lacks {k}")
        if E.get("spi_t") is not None and not (0 < E["spi_t"] < 5):
            failures.append(f"forecast: SPI(t) {E['spi_t']} out of any plausible range")
        # ES cannot be later than the status date when EV <= PV, and the sign of
        # SV(t) must agree with EV against PV.
        if E["ev_pct"] <= E["pv_pct"] and E["sv_t_days"] > 0:
            failures.append("forecast: SV(t) positive while earned is below planned")
        if not E.get("limits"):
            failures.append("forecast: the aggregate-measure limits are not declared")
    LA = fc["lookahead"]
    if len(LA) != 2 or LA[0]["weeks"] != 4 or LA[1]["weeks"] != 8:
        failures.append("forecast: look-ahead windows are not 4 and 8 weeks")
    elif LA[1]["must_start"] + LA[1]["must_finish"] < 1:
        failures.append("forecast: the 8-week window found nothing to start or finish in a fixture "
                        "with July activities")
    MB = fc["milestone_bands"]
    if MB.get("sample", 0) < 1 or not MB.get("milestones"):
        failures.append("forecast: milestone bands were not built from the slippage sample")
    else:
        m0 = MB["milestones"][0]
        if m0["p80"] < m0["p50"] or m0["p50"] < m0["finish"]:
            failures.append("forecast: milestone band is not ordered finish <= P50 <= P80")
    # The positive fixture's calendars carry one holiday and no reserved month: the
    # exposure must be declared unreadable, not reported as zero.
    RX = fc["rain_exposure"]
    if not RX.get("available"):
        failures.append("forecast: rain exposure not computed although calendars exist")
    if RX.get("readable") is not False or RX.get("unreadable_reason") != "no_reserve_months" \
            or RX.get("share_in_reserve_pct") is not None:
        failures.append("forecast: one holiday was read as a weather reserve, or zero was reported as exposure")

    # ---- forensics: driving path per milestone with a named origin, calendar
    # forensics, execution pattern; and, with a previous snapshot, float consumed
    # and milestone movement attributed to the chain.
    import forensics as forensics_mod
    fx = forensics_mod.build(pm, pos, None, None, None)
    m29 = next((m for m in fx["milestones"] if m["id"] == 29), None)
    if not m29:
        failures.append("forensics: the future milestone has no driving path")
    else:
        ids = [c["id"] for c in m29["chain"]]
        if ids[:3] != [29, 27, 26]:
            failures.append(f"forensics: driving chain {ids} != [29, 27, 26] through the lag link")
        if not m29["open_end"]:
            failures.append("forensics: the chain ends on an activity with no predecessor and was not flagged open")
        if not m29["origin"] or m29["origin"]["id"] != 29:
            failures.append("forensics: the delay origin should be the milestone itself (only it slipped)")
    if not fx["calendars"]:
        failures.append("forensics: calendar forensics produced nothing with two calendars in use")
    if fx["execution"]["start_slippage"]["sample"] < 1:
        failures.append("forensics: start slippage sample empty on a fixture with started activities")
    if fx["cycle"] is not None:
        failures.append("forensics: cycle forensics present without a previous snapshot")
    prev_m = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_prev.xml"))
    curr_m = parse_mspdi.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    curr_res = analyse_raw(curr_m)
    fx2 = forensics_mod.build(curr_m, curr_res, prev_m, cyc, None)
    if not fx2["cycle"] or "float_by_group" not in fx2["cycle"]:
        failures.append("forensics: cycle forensics missing with a previous snapshot")

    # ---- readings: rule-built sentences from the figures, in both languages, and
    # the executive synthesis slot that inject_narrative.py fills without recomputing.
    import narrative as narrative_mod
    full_en = report_data.build_review(pm, pos, grouping="DISCIPLINA", lang="en",
                                       phasing=curve, productivity=prod, quality=qres, forecast=fc,
                                       forensics=fx)
    full_pt = report_data.build_review(pm, pos, grouping="DISCIPLINA", lang="pt",
                                       phasing=curve, productivity=prod, quality=qres, forecast=fc,
                                       forensics=fx)
    for lang, full in (("en", full_en), ("pt", full_pt)):
        rd = full.get("readings") or {}
        for sec in ("verdict", "scurve", "groups", "productivity", "quality", "forecast", "forensics"):
            if not rd.get(sec):
                failures.append(f"readings: no {sec} reading in {lang}")
    if full_pt.get("readings", {}).get("verdict") and "network" in full_pt["readings"]["verdict"][0].lower():
        failures.append("readings: the Portuguese report got an English verdict sentence")
    if "narrative" not in full_en or full_en["narrative"] is not None:
        failures.append("readings: the synthesis slot is missing or pre-filled")

    # ---- the organisation profile: declared, validated, applied, and loud about a
    # field the file does not have.
    import profile as prof_mod
    prof = prof_mod.load(None)
    if prof_mod.validate(prof):
        failures.append("profile: the defaults do not validate")
    with tempfile.TemporaryDirectory() as tmp:
        pj = os.path.join(tmp, "profile.json")
        subprocess.run([sys.executable, os.path.join(HERE, "profile_tool.py"), "init", "--out", pj,
                        "--organisation", "Test Org"], check=True, capture_output=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, "profile_tool.py"), "set", pj,
                            "grouping=DISCIPLINA", "fields.discipline=DISCIPLINA",
                            "fields.section=NO_SUCH_FIELD", 'checks_optional=["B"]',
                            "threshold_days=10", 'sections_hidden=["v4"]', "theme.accent=#123456"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            failures.append(f"profile: set failed: {r.stderr.strip()}")
        bad = subprocess.run([sys.executable, os.path.join(HERE, "profile_tool.py"), "set", pj,
                              "ev_method=nonsense"], capture_output=True, text=True)
        if bad.returncode == 0:
            failures.append("profile: an invalid earned-value method was accepted")
        loaded = prof_mod.load(pj)
        if loaded["threshold_days"] != 10 or loaded["fields"]["discipline"] != "DISCIPLINA":
            failures.append("profile: values did not round-trip through the tool")
        pay = report_data.build_review(pm, pos, grouping=loaded["grouping"], lang="en", profile=loaded)
        if pay["meta"]["grouping_mode"] != "custom":
            failures.append("profile: grouping declared in the profile was not applied")
        if "section: NO_SUCH_FIELD" not in " ".join(pay["profile"]["fields_missing"]):
            failures.append("profile: a declared field the file lacks was not reported")
        bsev = next(f["severity"] for f in pay["findings"] if f["code"] == "B")
        if bsev != "high":
            failures.append("profile: checks_optional did not promote B to a finding")
        if pay["profile"]["sections_hidden"] != ["v4"]:
            failures.append("profile: hidden sections did not reach the payload")
        # A forced slot must be recorded as forced, so the report says whose choice it was.
        forced = prof_mod.deep_merge(loaded, {"baseline_slot": "1"})
        import copy
        m2 = copy.deepcopy(pm)
        m2["prevailing_baseline"] = {**m2["prevailing_baseline"], "slot": str(forced["baseline_slot"]),
                                     "basis": "forced by the organisation profile"}
        pay2 = report_data.build_review(m2, pos, grouping="wbs", lang="en", profile=forced)
        if pay2["profile"]["forced"].get("baseline_slot") != "1":
            failures.append("profile: a forced baseline slot was not declared in the payload")

    # ---- every entry script must run by path on an ISOLATED interpreter, from a
    # directory that is not its own. The embeddable Windows package ships a ._pth
    # file, which puts Python in isolated mode with no site and without the
    # script's folder on sys.path; -I -S reproduces exactly those three conditions.
    # A script that leans on the implicit path works on every developer machine
    # and fails on the one that needed the bundled interpreter.
    entry = sorted(f for f in os.listdir(HERE) if f.endswith(".py") and not f.startswith("test_")
                   and "__main__" in open(os.path.join(HERE, f), encoding="utf-8").read())
    with tempfile.TemporaryDirectory() as tmp:
        for f in entry:
            r = subprocess.run([sys.executable, "-I", "-S", os.path.join(HERE, f), "--help"],
                               capture_output=True, text=True, cwd=tmp)
            if r.returncode != 0:
                failures.append(f"isolated run: {f} does not start on an isolated interpreter: "
                                f"{(r.stderr.strip().splitlines() or ['?'])[-1]}")
        r = subprocess.run([sys.executable, "-I", "-S", os.path.join(HERE, "review.py"),
                            os.path.join(ROOT, "fixtures", "cycle_prev.xml"),
                            os.path.join(ROOT, "fixtures", "cycle_curr.xml"),
                            "--outdir", os.path.join(tmp, "out"), "--quiet"],
                           capture_output=True, text=True, cwd=tmp)
        made = os.listdir(os.path.join(tmp, "out")) if os.path.isdir(os.path.join(tmp, "out")) else []
        if r.returncode != 0 or sum(1 for f in made if f.endswith(".html")) != 2:
            failures.append("isolated run: review.py did not produce both reports on an isolated interpreter")

    # ---- a reading is only stated when the input it needs exists. bare.xml looks
    # complete and lacks four inputs; each must produce a sentence that says so, and
    # the confident sentence must be gone. The controls prove each confident
    # sentence still appears when its input is there.
    import forecast as fc_mod
    import i18n as i18n_m
    import phasing as ph_mod
    import run_checks as rc_mod
    bare_path = os.path.join(ROOT, "fixtures", "bare.xml")
    bm = parse_mspdi.parse(bare_path)
    bres = analyse_raw(bm)
    bcurve = ph_mod.build(bare_path, None)
    bq = quality_mod.build(bm, bare_path)
    bfc = fc_mod.build(bm, bcurve, None, None)
    for code in CODES:
        if code in ("A1", "A2") and bres["counts"][code]["distinct_activities"]:
            failures.append("bare: a schedule with no links raised a network finding")
    if bcurve["inputs"]["baseline_time_phased"] or bcurve["totals"]["planned_pct"] is not None \
            or bcurve["totals"]["spi"] is not None or bcurve["totals"]["sv"] is not None:
        failures.append("bare: a baseline with no time-phased cost produced a planned figure, SV or SPI")
    if bcurve["reconciliation"]["bcwp_comparable"] != 2 or bcurve["reconciliation"]["earned_equals_bcwp"] != 0:
        failures.append("bare: zero against zero was counted in the earned-value reconciliation")
    brx = bfc["rain_exposure"]
    if brx.get("readable") is not False or brx.get("unreadable_reason") != "no_exceptions" \
            or brx.get("share_in_reserve_pct") is not None:
        failures.append("bare: a calendar with no exception produced a rain-exposure share")
    for lang, gone, said in (
            ("en", ("The network holds", " ahead", "matched the file", "of the remaining cost"),
             ("no network", "Planned-to-date is unavailable", "compares nothing", "absence of data")),
            ("pt", ("A rede se sustenta", "à frente.", "bateu com", "do custo remanescente"),
             ("Não há rede", "indisponível", "não compara nada", "ausência de dado"))):
        bp = report_data.build_review(bm, bres, lang=lang, phasing=bcurve, quality=bq, forecast=bfc)
        text = " ".join(s for sec in bp["readings"].values() for s in sec)
        for g in gone:
            if g in text:
                failures.append(f"bare ({lang}): a reading without its input is still stated: '{g}'")
        for s_ in said:
            if s_ not in text:
                failures.append(f"bare ({lang}): the missing input is not declared: '{s_}'")
        mi = bp["meta"]["inputs"]
        if mi["network"]["state"] != "none" or mi["planned_available"] or mi["file_earned_value"]:
            failures.append(f"bare ({lang}): the inputs block does not say what is missing")
        rcb = bp["meta"]["reconciliation"]
        if rcb["file_computed_ev"] or rcb["matches_to_cent"] or rcb["both_zero_not_compared"] != 2 \
                or rcb["unexplained"]:
            failures.append(f"bare ({lang}): zero-against-zero counted as a match, or a missing "
                            "earned value reported as an unexplained gap")
        if bp["meta"]["percent_planned_file"] is not None:
            failures.append(f"bare ({lang}): planned percent is zero instead of unavailable")
    # Controls. The negative fixture is linked, costed, phased and reconciled: the
    # confident readings must be there.
    neg_path = os.path.join(ROOT, "fixtures", "negative.xml")
    nm = parse_mspdi.parse(neg_path)
    nres = analyse_raw(nm)
    ncurve = ph_mod.build(neg_path, None)
    npay = report_data.build_review(nm, nres, lang="en", phasing=ncurve,
                                    quality=quality_mod.build(nm, neg_path))
    ntext = " ".join(s for sec in npay["readings"].values() for s in sec)
    if "The network holds" not in ntext or npay["meta"]["inputs"]["network"]["state"] != "linked":
        failures.append("control: a linked, consistent schedule lost the 'network holds' reading")
    if "matched the file" not in ntext or not npay["meta"]["inputs"]["file_earned_value"]:
        failures.append("control: a file with its own earned value lost the reconciliation reading")
    if not npay["meta"]["inputs"]["planned_available"] or ncurve["totals"]["planned_pct"] is None:
        failures.append("control: a time-phased baseline was declared unavailable")
    # Linked but incomplete: the positive fixture without its violated pairs.
    pstate = report_data.network_state(pm, qres)
    if pstate["state"] != "open" or not pstate["unlinked"]:
        failures.append("network: missing logic above the threshold was not read as an open network")
    # A calendar that DOES reserve a month: the share is then a reading.
    import copy as copy_m
    wet = copy_m.deepcopy(nm)
    for day in ("2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09"):
        for cal in wet["calendars"]["definitions"].values():
            cal["exception_intervals"][day] = []
    wrx = fc_mod.rain_exposure(wet)
    if not wrx.get("readable") or not wrx.get("share_in_reserve_pct"):
        failures.append("control: a calendar with a reserved month gave no rain-exposure share")
    # The same status date in both deliveries, and its two neighbours.
    codes = {w["code"] for w in cyc["warning_codes"]}
    if "same_status_date" not in codes:
        failures.append("cycle: two deliveries with the same status date raised no warning")
    later = copy_m.deepcopy(curr_m)
    later["project"]["status_date"] = "2026-07-31T17:00:00"
    codes2 = {w["code"] for w in cs_mod.compare(prev_m, later)["warning_codes"]}
    if codes2 & {"same_status_date", "status_date_backwards"}:
        failures.append("cycle: two different status dates in the right order raised a status warning")
    codes3 = {w["code"] for w in cs_mod.compare(later, curr_m)["warning_codes"]}
    if "status_date_backwards" not in codes3:
        failures.append("cycle: a previous delivery dated AFTER the current one raised no warning")
    for lang in ("en", "pt"):
        if not any("status" in w["text"].lower() and "30" in w["text"]
                   for w in rd_mod.build_cycle(cyc, lang=lang)["warnings"]):
            failures.append(f"cycle ({lang}): the same-status-date warning is not in the report")
    # A finish that nothing drives is not called the end of a path.
    bcyc = cs_mod.compare(bm, copy_m.deepcopy(bm))
    if bcyc["project_finish"]["current"]["driver_linked"] is not False:
        failures.append("cycle finish: an unlinked last activity was presented as a driving path")
    if cyc["project_finish"]["current"]["driver_linked"] is not True:
        failures.append("cycle finish: a linked driver was presented as unlinked")
    # Number agreement, by the one helper.
    for tpl, kw, want in (
            ("{n} {n?atividade|atividades}", {"n": "1"}, "1 atividade"),
            ("{n} {n?atividade|atividades}", {"n": "2"}, "2 atividades"),
            ("{n} {n?atividade|atividades}", {"n": "0"}, "0 atividades"),
            ("{n} {n?dia|dias}", {"n": "1,0"}, "1,0 dia"),
            ("{n} {n?day|days}", {"n": "1,000"}, "1,000 days"),
            ("{a} of {n} {n?leaf|leaves}", {"a": 1, "n": 1}, "1 of 1 leaf")):
        if i18n_m.fmt(tpl, **kw) != want:
            failures.append(f"plural: {tpl!r} with {kw} did not give {want!r}")
    one = nar_mod.build({"meta": {}, "findings": [], "quality": {
        "metrics": [], "indices": {"bei": 1.0, "bei_due": 1, "bei_on_time": 1}}}, "pt")
    if not any("De 1 atividade devida" in s and "1 terminou" in s for s in one.get("quality", [])):
        failures.append(f"plural: the BEI reading does not agree with a count of one: {one.get('quality')}")
    # The baseline is named the way the tool names it, in every language.
    if i18n_m.baseline_name("pt", "1") != "linha de base 1" or i18n_m.baseline_name("pt", "0") != "linha de base" \
            or i18n_m.baseline_name("en", "3") != "baseline 3":
        failures.append("baseline: the name shown to a reader is not the tool's own")
    console = cs_mod.report(cyc) + "\n" + rc_mod.report(pos, "pt")
    if re.search(r"\d[.,]\d{3,}\s*%", console) or "aveta" in console:
        failures.append("console: a percentage with more than two decimals, or the storage word for the baseline")

    # ---- a reading holds only in the direction, or for the count, that supports it.
    # IEAC(t) earlier than the schedule's finish is not "the logic is optimistic";
    # high float with every milestone constrained is not "an unconstrained plan".
    def es_inputs(sched_finish):
        periods = [{"period": f"2027-{k:02d}", "planned": 10.0, "planned_cum_pct": 10.0 * k}
                   for k in range(1, 11)]
        sc = {"periods": periods, "status_date": "2027-05-31T17:00:00", "bac": 100.0,
              "totals": {"earned_pct": 50.0, "planned_pct": 50.0}}
        mdl = {"project": {"finish": sched_finish}, "prevailing_baseline": {"slot": "0"},
               "tasks": [{"baselines": {"0": {"finish": "2027-10-22T17:00:00"}}}]}
        return fc_mod.earned_schedule(sc, mdl)
    # IEAC(t) lands on 22/10 at midnight; the finish is at 17:00. The gap is counted
    # in calendar dates: a floored timedelta made three days earlier read as four.
    for fin, want_gap, want_read in (("2027-10-25T17:00:00", -3, "agree"),
                                     ("2027-10-19T17:00:00", 3, "agree"),
                                     ("2027-11-25T17:00:00", -34, "earlier"),
                                     ("2027-09-24T17:00:00", 28, "later")):
        E_ = es_inputs(fin)
        if E_.get("ieac_t_date") != "2027-10-22" or E_.get("gap_vs_schedule_days") != want_gap \
                or E_.get("gap_reading") != want_read:
            failures.append(f"ieac gap: finish {fin} gave {E_.get('ieac_t_date')}, "
                            f"{E_.get('gap_vs_schedule_days')} days, {E_.get('gap_reading')}; "
                            f"expected 2027-10-22, {want_gap}, {want_read}")
    ieac_said = {"later": {"en": ("logic is optimistic", "days after"), "pt": ("lógica está otimista", "dias depois")},
                 "earlier": {"en": ("days before", "carries margin"), "pt": ("dias antes", "carrega margem")},
                 "agree": {"en": ("agree on the date",), "pt": ("concordam na data",)}}
    ieac_gone = {"en": "logic is optimistic", "pt": "lógica está otimista"}
    for fin, read in (("2027-09-24T17:00:00", "later"), ("2027-11-25T17:00:00", "earlier"),
                      ("2027-10-25T17:00:00", "agree")):
        E_ = es_inputs(fin)
        for lang in ("en", "pt"):
            txt = " ".join(nar_mod.build({"meta": {}, "findings": [],
                                          "forecast": {"earned_schedule": E_}}, lang).get("forecast", []))
            for s_ in ieac_said[read][lang]:
                if s_ not in txt:
                    failures.append(f"ieac reading ({read}, {lang}): '{s_}' missing: {txt}")
            if read != "later" and ieac_gone[lang] in txt:
                failures.append(f"ieac reading ({read}, {lang}): concludes the logic is optimistic")
    # TSPI: "modest because most of the duration is ahead" only when it is.
    for at_, early_ in ((100, True), (450, False)):
        E_ = {"available": True, "sv_t_days": -10.0, "es_date": "2027-01-01", "spi_t": 0.95,
              "tspi": 1.05, "tspi_verdict": "hard", "at_days": at_, "pd_days": 568}
        for lang, word in (("en", "Modest because"), ("pt", "Modesto porque")):
            txt = " ".join(nar_mod.build({"meta": {}, "findings": [],
                                          "forecast": {"earned_schedule": E_}}, lang).get("forecast", []))
            if (word in txt) != early_ or "TSPI" not in txt:
                failures.append(f"tspi reading ({lang}, {at_}/568 elapsed): the 'most is ahead' clause "
                                f"{'is missing' if early_ else 'is stated late in the project'}")
    # A level Earned Schedule is neither ahead nor behind.
    lvl = nar_mod.build({"meta": {}, "findings": [], "forecast": {"earned_schedule": {
        "available": True, "sv_t_days": 0.2, "es_date": "2027-05-31", "spi_t": 1.0}}}, "pt").get("forecast", [])
    if not any("própria data de status" in s_ for s_ in lvl) or any("à frente" in s_ for s_ in lvl):
        failures.append(f"es reading: a level Earned Schedule was read as ahead: {lvl}")
    # Float against milestones: the conclusion needs a milestone without a deadline.
    def q_read(no_dl, status, lang):
        return " ".join(nar_mod.build({"meta": {}, "findings": [], "quality": {
            "metrics": [{"code": "Q6", "title": "High float", "share_pct": 12.0, "status": status}],
            "qualitative": {"milestones": 9, "milestones_without_deadline": no_dl}}}, lang).get("quality", []))
    for lang, concl, ask in (("en", "unconstrained plan", "read it as a question"),
                             ("pt", "plano sem restrição", "leia como pergunta")):
        t0, t3, tp = q_read(0, "fail", lang), q_read(3, "fail", lang), q_read(3, "pass", lang)
        if concl in t0 or ask not in t0 or "9 of 9" not in t0 and "9 de 9" not in t0:
            failures.append(f"float reading ({lang}): every milestone has a deadline, yet: {t0}")
        if concl not in t3 or "3 " not in t3:
            failures.append(f"float reading ({lang}): milestones without deadline lost the conclusion: {t3}")
        if "44" in tp:
            failures.append(f"float reading ({lang}): Q6 passes, yet the high float is read as a finding: {tp}")
    # No network state, and rates with no trend, support no reading at all.
    none_ = nar_mod.build({"meta": {}, "findings": [], "forecast": {"rates_by_group": [
        {"group": "G", "verdict": None}]}}, "en")
    if any("network holds" in s_ for s_ in none_.get("verdict", [])) or none_.get("forecast"):
        failures.append(f"readings: 'network holds' or 'every group on pace' stated without its input: {none_}")
    # Level progress, a reconciliation with nothing differing, a median start on the baseline.
    lv = nar_mod.build({"meta": {"percent_earned": 40.0, "percent_planned_file": 40.0,
                                 "inputs": {"planned_available": True},
                                 "reconciliation": {"leaves_compared": 5, "matches_to_cent": 5,
                                                    "unexplained": 0}},
                        "findings": [], "forensics": {"execution": {"start_slippage": {
                            "sample": 4, "started_early": 2, "started_late": 2, "p50": 0.2}}}}, "pt")
    vt, ft = " ".join(lv.get("verdict", [])), " ".join(lv.get("forensics", []))
    if "igual aos 40,00% previstos" not in vt or "atrás" in vt:
        failures.append(f"progress reading: level progress read with a direction: {vt}")
    if "explicada" in vt or "5 de 5 folhas" not in vt:
        failures.append(f"reconciliation reading: a difference was called explained where none exists: {vt}")
    if "caiu na data da linha de base" not in ft or "depois" in ft:
        failures.append(f"slippage reading: a median start on the baseline was given a direction: {ft}")

    # ---- one rounding rule: the reading and the tile beside it must agree (0.7.2).
    for v_, d_, lang_, want_ in ((0.9015, 3, "pt", "0,902"), (1.005, 2, "en", "1.01"),
                                 (2.675, 2, "pt", "2,68"), (-0.00004, 2, "pt", "0,00")):
        if nar_mod.fnum(v_, d_, lang_) != want_:
            failures.append(f"rounding: {v_} to {d_} read {nar_mod.fnum(v_, d_, lang_)}, the report shows {want_}")
    spi_ = " ".join(nar_mod.build({"meta": {}, "findings": [], "scurve": {"totals": {"spi": 0.9015}}},
                                  "pt").get("scurve", []))
    if "0,902" not in spi_ or "90,2%" not in spi_:
        failures.append(f"rounding: the SPI reading disagrees with its tile: {spi_}")
    # Group codes become group names; method sentences and attribution words are
    # localized on a copy, and the sidecar keeps the engine's own.
    fc_ = {"lookahead": [{"by_group": [{"group": "7"}], "starts": [{"group": "7"}], "finishes": []}],
           "earned_schedule": {"limits": "aggregate and cost-weighted"},
           "rain_exposure": {"reserve_rule": "x", "reserve_min_exceptions": 4,
                             "basis": "inferred: remaining cost spread"}}
    lf = rd_mod.localize_forecast(fc_, "pt", {"7": "Viaduct"})
    if lf["lookahead"][0]["by_group"][0]["group"] != "Viaduct" or fc_["lookahead"][0]["by_group"][0]["group"] != "7" \
            or "4 exce" not in lf["rain_exposure"]["reserve_rule"] or "aggregate" in lf["earned_schedule"]["limits"]:
        failures.append(f"localize: the forecast copy is not localized, or the sidecar was touched: {lf}")
    fxl = rd_mod.localize_forensics({"cycle": {"float_by_group": [{"group": "7"}], "milestone_movements": [
        {"attribution": "replan"}, {"attribution": "outside the chain"}]}}, "pt", {"7": "Viaduct"})
    if fxl["cycle"]["float_by_group"][0]["group"] != "Viaduct" or \
            [r["attribution"] for r in fxl["cycle"]["milestone_movements"]] != ["replanejamento", "fora da cadeia"] \
            or "reconstrução" not in fxl["provenance"]:
        failures.append(f"localize: forensics groups, attribution or provenance left raw: {fxl}")

    # ---- the leftover readings (0.7.2): each missing input gets a neutral sentence,
    # never a fallback to a claim.
    def rd(payload, lang, sec):
        return " ".join(nar_mod.build({"meta": {}, "findings": [], **payload}, lang).get(sec, []))
    t_ = rd({"forecast": {"earned_schedule": {"available": True, "sv_t_days": -5.0, "es_date": "2027-01-01",
                                              "spi_t": 0.9, "tspi": 1.05, "tspi_verdict": None}}}, "pt", "forecast")
    if "acima do plano" in t_ or "O TSPI é 1,050" not in t_:
        failures.append(f"tspi reading: an unknown verdict fell back to the hard sentence: {t_}")
    t_ = rd({"forensics": {"summary": {"milestones": 4, "with_origin": 2, "origins": []}}}, "pt", "forensics")
    if "Nenhum marco futuro carrega" in t_ or "2 de 4" not in t_:
        failures.append(f"forensics reading: origins found but unlisted read as none: {t_}")
    t_ = rd({"forensics": {"summary": {"milestones": 4, "with_origin": 2, "origins": [
        {"id": 148, "name": "Bored piles", "milestones": 2}]}}}, "en", "forensics")
    if "activity 148, Bored piles," not in t_:
        failures.append(f"forensics reading: the origin activity is not named: {t_}")
    t_ = rd({"quality": {"metrics": [{"code": "Q6", "share_pct": 12.0, "status": "fail"},
                                     {"code": "Q11", "status": "fail"}],
                         "qualitative": {"milestones": 0}}}, "pt", "quality")
    if "Q11 ," in t_ or "Q11." not in t_ or "nenhum marco" not in t_.lower() and "não tem marco" not in t_:
        failures.append(f"quality reading: a missing title or zero milestones read badly: {t_}")

    # ---- an actual date rewritten onto the baseline, and a variance measured against
    # a baseline that moved (0.7.2). Row 16 had its actual finish moved AWAY from the
    # baseline in the fixture (not flagged); here it is moved ONTO it (flagged).
    pv5 = copy_mod.deepcopy(pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_prev.xml")))
    cv5 = copy_mod.deepcopy(pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml")))
    for t in pv5["tasks"]:
        if t["uid"] == 16:
            t["actual_finish"] = "2026-04-14T17:00:00"
    for t in cv5["tasks"]:
        if t["uid"] == 16:
            t["actual_finish"] = t["baselines"]["1"]["finish"]
    c5 = cs_mod.compare(pv5, cv5)
    flagged = [r["id"] for r in c5["past_rewritten"]["actual_finish"] if r["matches_baseline"]]
    if flagged != [16] or any(r["matches_baseline"] for r in cyc["past_rewritten"]["actual_finish"]):
        failures.append(f"cycle past: an actual date rewritten onto the baseline not flagged, or a control flagged: {flagged}")
    for lang, word in (("en", "exactly on the baseline date (row 16"), ("pt", "coincidir exatamente com a linha de base (linha 16")):
        if word not in " ".join(nar_mod.build_cycle(c5, lang, rd_mod.fmt_date).get("c5", [])):
            failures.append(f"cycle past reading ({lang}): the date rewritten onto the baseline is not said")
    import forensics as fx_mod5
    cv0 = pm_mod.parse(os.path.join(ROOT, "fixtures", "cycle_curr.xml"))
    fx5 = fx_mod5.build(cv0, analyse_raw(cv0), pv5, {"baseline_moved": [
        {"uid": 7, "id": 7, "baseline_finish_moved_days": 12.0}], "trend": []})
    marked5 = [n["id"] for m_ in fx5["milestones"] for n in m_["chain"] if n.get("baseline_moved_days")]
    if marked5 != [7]:
        failures.append(f"forensics: a chain row whose baseline moved is not marked: {marked5}")
    for lang, word in (("en", "the reference moving"), ("pt", "a referência se movendo")):
        txt = " ".join(nar_mod.build({"meta": {}, "findings": [], "forensics": fx5}, lang).get("forensics", []))
        if word not in txt or "+12" not in txt:
            failures.append(f"forensics reading ({lang}): the moved baseline is not cross-referenced: {txt}")

    # ---- the network gate is as wide as the breach (0.7.2). One pair off the
    # critical path and off the finish chain is named, with the milestones whose
    # chain passes through it; on the critical path, or above the threshold, the
    # absolute wording stays.
    gate_model = pm_mod.parse(os.path.join(ROOT, "fixtures", "positive.xml"))
    gate_res = analyse_raw(gate_model)
    g_abs = rd_mod.network_gate(gate_model, gate_res)
    if g_abs["scope"] != "absolute" or "total_inversion" not in g_abs["reasons"]:
        failures.append(f"network gate: total inversion did not keep the absolute wording: {g_abs}")
    one = copy_mod.deepcopy(gate_res)
    one["pairs"]["A1"] = one["pairs"]["A1"][:1]
    one["counts"]["A2"]["distinct_activities"] = 0
    pair_uids = {one["pairs"]["A1"][0]["successor_uid"], one["pairs"]["A1"][0]["predecessor_uid"]}
    side = copy_mod.deepcopy(gate_model)
    for t in side["tasks"]:
        if t["uid"] in pair_uids:
            t["critical"], t["total_slack_minutes"] = False, 4800.0
    fake_fx = {"milestones": [{"id": 99, "name": "Milestone M", "chain": [{"uid": u} for u in pair_uids]}]}
    g_sc = rd_mod.network_gate(side, one, fake_fx)
    if g_sc["scope"] != "scoped" or [m_["id"] for m_ in g_sc["milestones"]] != [99]:
        failures.append(f"network gate: one side-branch pair was read as a broken network: {g_sc}")
    for t in side["tasks"]:
        if t["uid"] in pair_uids:
            t["critical"] = True
    if rd_mod.network_gate(side, one, fake_fx)["scope"] != "absolute":
        failures.append("network gate: a pair on the critical path lost the absolute wording")
    many = copy_mod.deepcopy(one)
    many["pairs"]["A1"] = one["pairs"]["A1"] * (rd_mod.GATE_MAX_PAIRS + 1)
    if "count" not in rd_mod.network_gate(gate_model, many)["reasons"]:
        failures.append("network gate: more pairs than the threshold did not keep the absolute wording")
    scoped_gate = {"scope": "scoped", "pair_count": 1, "threshold_pairs": rd_mod.GATE_MAX_PAIRS,
                   "pairs": [{"succ_id": 36, "succ_name": "Prime coat", "pred_id": 35,
                              "pred_name": "Base course"}],
                   "milestones": [{"id": 5, "name": "Opening S1"}, {"id": 6, "name": "Opening S2"}]}
    for lang, absolute, words in (("en", "settle these before discussing a date", ("row 36", "Opening S2 (row 6)")),
                                  ("pt", "resolva isso antes de discutir uma data", ("linha 36", "Opening S2 (linha 6)"))):
        base = {"findings": [{"code": "A1", "count": 2}, {"code": "A2", "count": 0}]}
        sc_ = " ".join(nar_mod.build({**base, "meta": {"inputs": {"network_gate": scoped_gate}}}, lang)["verdict"])
        ab_ = " ".join(nar_mod.build({**base, "meta": {"inputs": {"network_gate": {
            **scoped_gate, "scope": "absolute", "reasons": ["critical"]}}}}, lang)["verdict"])
        if absolute in sc_ or not all(w_ in sc_ for w_ in words):
            failures.append(f"network gate reading ({lang}): one side pair is not named and scoped: {sc_}")
        if absolute not in ab_ or "36" not in ab_:
            failures.append(f"network gate reading ({lang}): a critical pair lost the absolute wording: {ab_}")

    # ---- the report must actually render. A valid file that runs to a blank page
    # is the failure mode this guards; see scripts/test_render.js for the real bug.
    rendered = render_checks()
    failures.extend(rendered["failures"])

    # Required rate and projection count the same days: the status day is spent.
    # Found by an agent in secret mode on 22/11/2026 (activity 149 of the example):
    # practised rate above the required one, verdict still "critical".
    from datetime import datetime as _dt
    import resources as _res
    _st = _dt(2026, 11, 3, 17, 0)
    _end = _dt(2026, 11, 10, 17, 0)
    _days = _res.working_days_after(None, _st, _end)
    if _days != 7:
        failures.append(f"required rate: days after the status date should be 7, got {_days}")
    for _qty, _rate in ((137.6, 21.474), (140.0, 20.0), (150.0, 20.0), (139.9, 20.0), (5.0, 0.7)):
        _req = _qty / _days
        _proj = _res.add_working_days(None, _st, _qty / _rate)
        if (_rate >= _req) != (_proj <= _end):
            failures.append(f"required rate: rate {_rate} vs required {_req:.3f} disagrees with "
                            f"the projection {_proj:%Y-%m-%d} against {_end:%Y-%m-%d}")

    # ---- a .mpp goes through MS Project itself (Windows). Off Windows, nothing is
    # exported: a .mpp keeps the old route, and "the schedule open in Project" says why not.
    import mpp_export
    if not mpp_export.needs_export("Rev04.MPP") or mpp_export.needs_export("Rev04.xml"):
        failures.append("mpp export: a .mpp is not recognised as needing export, or an .xml is")
    xs, origins, tmp, _ = mpp_export.prepare([os.path.join(ROOT, "fixtures", "positive.xml")])
    if tmp is not None or xs != [os.path.join(ROOT, "fixtures", "positive.xml")]:
        failures.append("mpp export: an .xml input was touched")
    if os.name != "nt":
        xs, origins, tmp, _ = mpp_export.prepare(["x.mpp"])
        if tmp is not None or xs != ["x.mpp"]:
            failures.append("mpp export: off Windows a .mpp must keep the old route")
        try:
            mpp_export.prepare([mpp_export.ACTIVE], "pt")
            failures.append("mpp export: the open project was exported off Windows")
        except mpp_export.ExportError as exc:
            if "Windows" not in str(exc):
                failures.append(f"mpp export: off Windows the message does not say why: {exc}")
    for lang in ("en", "pt"):
        if set(mpp_export.MESSAGES[lang]) != set(mpp_export.MESSAGES["en"]):
            failures.append(f"mpp export: messages differ between en and {lang}")

    # ---- modes: free and secret. The preference file, and a run that must not read.
    failures.extend(mode_checks())
    secret = secret_checks()
    failures.extend(secret["failures"])

    # ---- the worked example a reader runs first: what its README lists as planted
    # is what the engine finds.
    example = example_checks()
    failures.extend(example["failures"])

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  * {f}")
        return 1

    print("PASS")
    print(f"  positive: all {len(CODES)} checks fired, both link ends marked")
    print(f"  negative: all {len(CODES)} checks silent on a consistent schedule")
    print("  transversal rule: pending record did not raise a network finding")
    print("  cycle: execution, replan and rebased-baseline all detected; residue named")
    print("  cycle model: finish and driver, critical path, logic, duration, rewritten past, quality")
    print("  cycle control: a file against itself is silent; no path, raw date or negative zero shown")
    print("  inputs: no network, no file EV, no time-phased baseline, no reserve -> said, not read as zero")
    print("  wording: number agreement by one helper; baseline named as the tool names it; two decimals")
    print("  report: no external references, so it works offline")
    print(f"  isolated run: {len(entry)} entry scripts start with -I -S from another folder; review end to end")
    if rendered["skipped"]:
        print("  report render: SKIPPED (node not installed) -- the blank-page guard did not run")
    else:
        print("  report render: both reports executed and produced every expected section")
    if example["skipped"]:
        print("  example: SKIPPED (no examples folder beside this copy of the skill)")
    else:
        print("  example: the fictitious road pair is what its generator writes; every planted problem found")
    print("  calendars: 9h six-day week and its holiday applied; consistent task not flagged")
    print("  language: pt and en detected from content; every label present in both")
    print("  fields: discovery typed and ranked them; grouping by alias and by a missing name")
    print("  network: lead honoured, both-complete ignored and recorded, SS lag violation caught")
    print("  reconciliation: file BCWP read, ahead-of-baseline classified, no unexplained gap")
    print("  phasing: blocks equal cost and BCWS on every task; sentinel dropped; curve rendered")
    print("  money: read in hundredths, divided once; absolute figures /100, every ratio identical")
    print("  productivity: quantities from the ISO hours, three rates, projection and verdicts")
    print("  quality: fourteen metrics with controls; Q12 and Q13 declared not computable")
    print("  forecast: earned schedule, look-ahead, rates, milestone bands, rain exposure")
    print("  forensics: driving chain through the lag link, origin named, cycle readings")
    print("  readings: every section reads in both languages; synthesis injected without recompute")
    print("  directions: IEAC(t) later/earlier/agree, float vs deadlines, level progress/ES/slip, TSPI clause")
    print("  profile: init/set/validate round-trip; grouping, fields, optional checks and hiding applied")
    print("  modes: preference set, read and survived a corrupt file; --secret and a stored 'on' stop")
    print("         without reading inside an agent and run a coded work folder outside one;")
    print("         'ask' with no terminal says one line on stderr and goes on")
    t = secret["totals"]
    print(f"  secret (experimental): {t['runs']} runs, {t['sidecars']} sidecars and {t['reports']} reports "
          f"decoded equal to free mode ({t['values_equal']} report values); no text, date, money or")
    print("         path of the files in any work folder or output; guard allows the session's work and")
    print("         blocks the vault, the original, interpreters, variables and `text`; collisions resolved")
    print("         (program words and coded figures equal to a real one by chance are excused, by rule)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
