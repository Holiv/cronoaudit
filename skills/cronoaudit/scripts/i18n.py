#!/usr/bin/env python3
"""Report language, detected from the schedule rather than configured.

A schedule written in Portuguese should produce a report in Portuguese. Nobody
should have to set a flag for that, and a flag would be wrong as often as it is
right, because the person running the review is frequently not the person who
wrote the file.

Detection is a stopword and diacritic score over the text the file already carries:
activity names, calendar names, the project title. No dependency, no network, and a
declared fallback when the evidence is thin -- the report states which language it
chose and how confident the evidence was, so a wrong guess is visible rather than
silent.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Function words are the signal. Content words drift between domains; "de" and
# "the" do not. Kept short deliberately: a longer list does not improve the
# decision and invites arguing about vocabulary.
MARKERS = {
    "pt": {
        "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas", "para",
        "com", "por", "ao", "aos", "à", "às", "um", "uma", "os", "as", "que", "sem",
        "obra", "obras", "serviço", "serviços", "execução", "projeto", "implantação",
        "instalação", "concreto", "terraplenagem", "drenagem", "sinalização",
        "início", "término", "prazo", "etapa", "marco", "trecho", "faixa",
    },
    "en": {
        "the", "of", "and", "to", "in", "on", "for", "with", "by", "a", "an", "is",
        "works", "work", "service", "services", "execution", "project", "installation",
        "concrete", "earthworks", "drainage", "signage", "start", "finish", "duration",
        "phase", "milestone", "section", "lane",
    },
}

# Characters that occur in Portuguese and essentially never in English text.
PT_DIACRITICS = set("ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ")

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def detect(model: dict, sample: int = 1200) -> dict:
    """Choose a language from the file's own text.

    Returns the chosen code, the scores, and how much evidence there was, so the
    report can say what it decided instead of deciding invisibly.
    """
    texts = []
    project = model.get("project") or {}
    for key in ("title", "name"):
        if project.get(key):
            texts.append(project[key])
    for cal in (model.get("calendars") or {}).get("in_use", []):
        if cal.get("name"):
            texts.append(cal["name"])
    for task in (model.get("tasks") or [])[:sample]:
        if task.get("name"):
            texts.append(task["name"])

    blob = " ".join(texts)
    words = [w.lower() for w in _WORD.findall(blob)]
    counts = Counter(words)

    scores = {}
    for lang, markers in MARKERS.items():
        scores[lang] = sum(counts[w] for w in markers)

    diacritics = sum(1 for ch in blob if ch in PT_DIACRITICS)
    # Diacritics are strong but not decisive on their own: a proper noun can carry
    # them in an otherwise English file. Weighted, not treated as proof.
    scores["pt"] += diacritics * 2

    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    margin = (scores[best] - max(v for k, v in scores.items() if k != best)) if len(scores) > 1 else 0
    if total < 10:
        # Thin evidence: say so and fall back rather than guessing from noise.
        return {
            "lang": "en", "scores": scores, "words": len(words),
            "diacritics": diacritics, "confidence": "low",
            "basis": "too little text to judge; defaulted to English",
        }
    return {
        "lang": best,
        "scores": scores,
        "words": len(words),
        "diacritics": diacritics,
        "confidence": "high" if margin > total * 0.25 else "moderate",
        "basis": "function-word and diacritic score over activity, calendar and project names",
    }


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


# ---------------------------------------------------------------------------
# Finding text, per language. The code is the stable identifier; these are the
# words a person reads.
# ---------------------------------------------------------------------------
FINDINGS = {
    "en": {
        "A1": ("Execution out of sequence",
               "A successor started before its predecessor finished",
               "Successor has an actual start; the predecessor has no actual finish. Both ends "
               "of the violated link are listed.",
               "Actual Start, predecessor Actual Finish, Predecessor Link",
               "Group by predecessor and filter on Actual Start present. In the schedule, flag "
               "the pair and inspect the link in the Gantt."),
        "A2": ("Total inversion",
               "A successor is complete while its predecessor never started",
               "Successor has an actual finish; the predecessor has no actual start.",
               "Actual Finish, predecessor Actual Start, Predecessor Link",
               "Filter Actual Finish present, then check each predecessor's Actual Start."),
        "H": ("Trend elapsed with no progress",
              "Dates in the past that never happened",
              "Finish is earlier than the status date, with neither an actual start nor an "
              "actual finish.",
              "Finish, Actual Start, Actual Finish, project Status Date",
              "Insert the Status Date field, filter Finish before it, and add Actual Start and "
              "Actual Finish as columns to confirm both are blank."),
        "E": ("Pulled forward and never started",
              "The forecast moved earlier with no execution behind it",
              "Finish minus baseline finish is at or below minus the threshold, and there is no "
              "actual start.",
              "Finish, Baseline Finish, Actual Start, and the activity's own Calendar column",
              "Insert Finish Variance. Filter at or below minus the threshold with Actual Start "
              "blank."),
        "C": ("Delayed beyond the threshold",
              "Material slippage against the baseline",
              "Finish minus baseline finish is at or above the threshold.",
              "Finish, Baseline Finish, and the activity's own Calendar column",
              "Insert Finish Variance and filter at or above the threshold."),
        "G": ("Duration incompatible with the window",
              "Thermometer of reprogramming, not a finding on its own",
              "The duration disagrees with the working time between start and finish, measured "
              "on the activity's own calendar, by more than the tolerance.",
              "Duration, Start, Finish, and the activity's own Calendar column",
              "Show Duration, Start, Finish and Calendar side by side. The span must be measured "
              "in that calendar's working time, not in days."),
        "B": ("Milestone with no deadline",
              "Nothing in the file makes this date binding",
              "The task is a milestone and no deadline is set.",
              "Milestone, Deadline",
              "Filter on Milestone, insert the Deadline column, and sort by it."),
        "F": ("In progress at zero percent",
              "Started, but reporting no progress at all",
              "There is an actual start, no actual finish, and percent complete is zero.",
              "Actual Start, Actual Finish, Percent Complete",
              "Filter Actual Start present and Percent Complete equal to zero."),
        "P": ("Pending record",
              "One hundred percent physical with no actual finish",
              "Percent complete is one hundred and there is no actual finish.",
              "Physical Percent Complete, Actual Finish",
              "Insert Physical Percent Complete and Actual Finish, and filter one hundred with "
              "the finish blank."),
    },
    "pt": {
        "A1": ("Execução fora de sequência",
               "Uma sucessora começou antes de a predecessora terminar",
               "A sucessora tem início real e a predecessora não tem término real. As duas "
               "pontas do vínculo violado são listadas.",
               "Início Real, Término Real da predecessora, Vínculo de Predecessora",
               "Agrupe por predecessora e filtre por Início Real preenchido. No cronograma, "
               "marque o par e inspecione o vínculo no Gantt."),
        "A2": ("Inversão total",
               "Uma sucessora está concluída e a predecessora nunca começou",
               "A sucessora tem término real e a predecessora não tem início real.",
               "Término Real, Início Real da predecessora, Vínculo de Predecessora",
               "Filtre por Término Real preenchido e confira o Início Real de cada "
               "predecessora."),
        "H": ("Tendência vencida sem realização",
              "Datas no passado que nunca aconteceram",
              "O término é anterior à data de status, sem início real e sem término real.",
              "Término, Início Real, Término Real, Data de Status do projeto",
              "Insira a Data de Status, filtre Término anterior a ela e acrescente as colunas "
              "Início Real e Término Real para confirmar que as duas estão vazias."),
        "E": ("Antecipada e nunca iniciada",
              "A tendência foi puxada para antes sem execução por trás",
              "O término menos o término da linha de base está igual ou abaixo do limiar "
              "negativo, e não há início real.",
              "Término, Término da Linha de Base, Início Real e a coluna Calendário da própria "
              "atividade",
              "Insira a Variação de Término. Filtre igual ou abaixo do limiar negativo com "
              "Início Real vazio."),
        "C": ("Atrasada além do limiar",
              "Escorregão relevante contra a linha de base",
              "O término menos o término da linha de base está igual ou acima do limiar.",
              "Término, Término da Linha de Base e a coluna Calendário da própria atividade",
              "Insira a Variação de Término e filtre igual ou acima do limiar."),
        "G": ("Duração incompatível com a janela",
              "Termômetro de reprogramação, não um achado por si só",
              "A duração divergente do tempo útil entre início e término, medido no calendário "
              "da própria atividade, acima da tolerância.",
              "Duração, Início, Término e a coluna Calendário da própria atividade",
              "Mostre Duração, Início, Término e Calendário lado a lado. A janela tem de ser "
              "medida no tempo útil daquele calendário, não em dias."),
        "B": ("Marco sem data limite",
              "Nada no arquivo torna esta data vinculante",
              "A tarefa é um marco e não tem Data Limite preenchida.",
              "Marco, Data Limite",
              "Filtre por Marco, insira a coluna Data Limite e ordene por ela."),
        "F": ("Em andamento com zero por cento",
              "Começou, mas não reporta avanço nenhum",
              "Existe início real, não existe término real e o percentual concluído é zero.",
              "Início Real, Término Real, % Concluída",
              "Filtre por Início Real preenchido e % Concluída igual a zero."),
        "P": ("Apontamento pendente",
              "Cem por cento físico sem término real",
              "O percentual concluído é cem e não existe término real.",
              "% Física Concluída, Término Real",
              "Insira % Física Concluída e Término Real e filtre cem com o término vazio."),
    },
}

LAYERS = {
    "en": {"net": "Network integrity", "date": "Date adherence", "rep": "Reporting consistency"},
    "pt": {"net": "Integridade da rede", "date": "Aderência de data",
           "rep": "Consistência de apontamento"},
}

SEVERITY_WORDS = {
    "en": {"critical": "critical", "high": "high", "check": "check", "pending": "pending",
           "view": "view"},
    "pt": {"critical": "crítico", "high": "alto", "check": "verificação",
           "pending": "pendência", "view": "visão"},
}

# Relationship types, as the tool names them in each language. In Portuguese
# Project the same links read TI, II, TT and IT, and a planner reads those, not
# the English codes.
LINK_TYPES = {
    "en": {"FS": "FS", "SS": "SS", "FF": "FF", "SF": "SF"},
    "pt": {"FS": "TI", "SS": "II", "FF": "TT", "SF": "IT"},
}


def link_type(lang: str, code: str) -> str:
    return LINK_TYPES.get(lang, LINK_TYPES["en"]).get(code, code)


def findings_text(lang: str) -> dict:
    return FINDINGS.get(lang, FINDINGS["en"])


def layers(lang: str) -> dict:
    return LAYERS.get(lang, LAYERS["en"])


def severity_words(lang: str) -> dict:
    return SEVERITY_WORDS.get(lang, SEVERITY_WORDS["en"])


# ---------------------------------------------------------------------------
# Report interface strings. Keys are stable; the words are what a person reads.
# The template holds no prose of its own, so adding a language means adding a
# block here and nothing else.
# ---------------------------------------------------------------------------
UI = {
    "en": {
        "review_title": "Schedule integrity review",
        "chip_title": "Schedule critical analysis",
        "reading": "Reading",
        "profile_missing": "The profile names fields this schedule does not have:",
        "col_rate_contracted": "Rate contracted",
        "syn_label": "Executive synthesis",
        "syn_written": "Written by {who} from the figures in this report, {when}.",
        "fx_title": "Forensics of the scenario",
        "fx_sub": "Where did the delay come from, by which path, and when did it start? Not a "
                  "contractual delay claim, which needs contemporaneous records and a formal "
                  "method: a reconstruction of the mechanism, with reproducible evidence, to "
                  "sustain the meeting and the notification.",
        "fx_paths_title": "Driving path per milestone",
        "fx_paths_sub": "From each future milestone, back through the predecessor that actually "
                        "drives each start, until the chain reaches an activity that has "
                        "started or an open end. The origin is the deepest activity on the "
                        "chain still carrying at least {n} working days of variance: the delay "
                        "has a name, not an aggregate.",
        "fx_origins": "Activities originating delay on the most milestones",
        "col_milestones_n": "Milestones", "col_origin": "Origin", "col_origin_var": "Origin var. (d)",
        "col_chain": "Chain", "col_open_end": "Open end", "col_reaches": "Reaches started work",
        "col_amplifier": "Grew most at", "col_added": "Added (d)",
        "fx_chain_show": "Show the driving chain",
        "col_via": "Via", "col_var_days": "Var. (d)", "col_started": "Started",
        "fx_cal_title": "Calendar forensics",
        "fx_cal_sub": "A productivity reserve registered for one year while the activities on "
                      "that calendar execute in another embeds optimism nothing in the file "
                      "announces. Per calendar: non-working exceptions per year against "
                      "activity-days per year.",
        "col_year": "Year", "col_activity_days": "Activity-days", "col_reserve_days": "Reserve days",
        "col_flags": "Flags",
        "fx_exec_title": "Execution pattern",
        "fx_exec_sub": "Out-of-sequence execution by the month the successor started, and the "
                       "distribution of start slippage against the baseline: {n} started "
                       "activities, P50 {p50} days, P80 {p80} days; {early} started early, "
                       "{late} late.",
        "col_pairs": "Pairs in the count", "col_ignored": "Both complete, recorded",
        "fx_cycle_title": "This cycle: float consumed and milestone movement",
        "fx_cycle_sub": "Between the two snapshots: float consumed per group, activities that "
                        "became critical, and the movement of each milestone attributed to what "
                        "moved on its driving chain: execution, replan, or a moved reference.",
        "col_float_before": "Float before", "col_float_now": "Float now", "col_consumed": "Consumed (d)",
        "col_moved": "Moved (d)", "col_attribution": "Attribution", "col_finish_before": "Finish before",
        "col_finish_now": "Finish now", "fx_became_critical": "Became critical this cycle",
        "fc_title": "Looking forward",
        "fc_sub": "Five readings from data the file already carries. Earned Schedule asks on "
                  "what date the planned curve reached the value earned today; that date, set "
                  "against the elapsed time, gives a schedule efficiency and an independent "
                  "finish that is compared with the schedule's own, never used in its place. "
                  "The look-ahead says what the next weeks demand. The rates say where the "
                  "practised pace does not reach the required one. The milestone bands apply "
                  "the slippage this snapshot has already shown. The rain exposure says how "
                  "much of what remains sits in months the calendars reserve for bad weather.",
        "es_title": "Earned Schedule",
        "es_es": "Earned Schedule", "es_es_cap": "date the plan reached today's earned value",
        "es_sv": "SV(t)", "es_sv_cap": "days behind the plan, in time",
        "es_spi": "SPI(t)", "es_spi_cap": "schedule efficiency to date",
        "es_ieac": "IEAC(t)", "es_ieac_cap": "independent finish at this efficiency",
        "es_tspi": "TSPI", "es_tspi_cap": "efficiency the remainder needs to finish as planned",
        "es_schedule": "Schedule's own finish", "es_planned": "Planned finish",
        "es_gap": "The independent finish lands {n} days from the schedule's own finish. The "
                  "gap is the conversation: either the logic is optimistic, or the remainder "
                  "will run at a pace not yet seen.",
        "es_limits": "Limits.",
        "tspi_recoverable": "recoverable", "tspi_hard": "hard", "tspi_unrecoverable": "unrecoverable in practice",
        "la_title": "Look-ahead", "la_window": "{w} weeks, {a} to {b}",
        "la_start": "Must start", "la_finish": "Must finish", "la_planned": "Planned earning",
        "la_projected": "At the practised rate", "la_reachable": "reachable", "la_not_reachable": "not reachable",
        "col_starts": "Starts", "col_finishes": "Finishes", "col_start": "Start",
        "rg_title": "Practised pace against required pace, by group",
        "rg_sub": "Earned percent per week to date, against the percent per week the remainder "
                  "needs to land on the group's baseline finish. One number per group says "
                  "whether there is time.",
        "col_practised": "Practised %/wk", "col_required": "Required %/wk", "col_ratio": "Required ÷ practised",
        "col_weeks_left": "Weeks left", "rg_on_pace": "on pace", "rg_stretch": "stretch", "rg_out": "out of reach",
        "mb_title": "Milestones with a confidence band",
        "mb_sub": "The distribution of finish slippage already observed in this snapshot, "
                  "applied to each future milestone's current finish: P50 {a} days, P80 {b} "
                  "days, from {n} activities. Not a simulation with an invented premise.",
        "col_slip_now": "Slip now (d)", "col_p50": "P50", "col_p80": "P80", "col_deadline": "Deadline",
        "col_critical": "Critical",
        "rx_title": "Exposure to the rainy season",
        "rx_sub": "Remaining cost spread over each activity's current span, read against the "
                  "months its own calendar reserves for bad weather ({rule}).",
        "rx_now": "In reserve months now", "rx_shift": "If everything slips 30 days",
        "col_remaining": "Remaining", "col_in_reserve": "In reserve", "col_share_reserve": "Share",
        "quality_title": "Network quality",
        "quality_sub": "Does this schedule hold up as a model, before any date is discussed? "
                       "The mechanical metrics of the DCMA 14-point assessment, each with its "
                       "formula and its published threshold, plus what a planner asks of any "
                       "schedule. This is an implementation of the metrics, not a certification "
                       "against the standard: thresholds are quoted so they can be argued with, "
                       "and what cannot be computed from a file is said, not approximated.",
        "col_metric": "Metric", "col_count": "Count", "col_population": "Of", "col_share": "Share",
        "col_threshold": "Threshold", "col_status": "Status", "q_pass": "pass", "q_fail": "fail",
        "q_na": "not computable", "q_info": "count only",
        "tile_bei": "Baseline execution index", "tile_cpli": "Critical path length index",
        "tile_critical_n": "Critical activities, incomplete", "tile_open_ends": "Open ends",
        "bei_cap": "{a} on time of {d} due", "cpli_cap_na": "no deadline on the finish milestone",
        "cpli_cap": "critical path {d} days",
        "crit_reaches": "The critical chain reaches the final milestone.",
        "crit_not_reaches": "The critical chain does not reach the final milestone: the network "
                            "is not whole, or the finish is constrained elsewhere.",
        "soft_constraints": "{n} soft constraints (start or finish no earlier than) also present; "
                            "counted, not failed.",
        "summaries_links": "{n} summary tasks carry links. Logic belongs on activities.",
        "show_items": "Show the {n} items",
        "prod_title": "Productivity and trend by resource",
        "prod_sub": "Quantities come from the file's own assignments: for a material resource "
                    "the tool stores the quantity in the work fields. Three rates per activity, "
                    "because one is not a fair reading: what this activity has practised, what "
                    "the resource has practised everywhere, and the resource's last {n} days. "
                    "The projection runs the remaining quantity over each rate on the activity's "
                    "own calendar and reads the result against four dates.",
        "prod_verdict_intro": "Three verdicts, in order of gravity. After the trend finish but not "
                              "after the baseline finish: reprogram, no baseline delay. After the "
                              "baseline finish but not after the late finish: the float absorbs it, "
                              "and the column says how much is left. After the late finish: the "
                              "activity enters the critical path, on the date shown.",
        "v_ahead": "ahead", "v_reprogram": "reprogram", "v_baseline_delay": "baseline delay, float absorbs",
        "v_critical": "enters critical path", "v_none": "no rate yet",
        "tile_resources": "Resources tracked", "tile_projected": "Activities projected",
        "tile_critical": "Would enter the critical path", "tile_inferred": "Executed inferred from percent",
        "prod_resources_title": "Rates by resource",
        "col_resource": "Resource", "col_unit": "Unit", "col_assign": "Assign.",
        "col_planned_qty": "Planned", "col_exec_qty": "Executed", "col_rem_qty": "Remaining",
        "col_rate_global": "Rate to date", "col_rate_recent": "Rate recent", "col_rate_planned": "Rate planned",
        "col_progress": "Progress %",
        "prod_activities_title": "Activities in progress, projected",
        "col_rate_own": "Rate own", "col_req_trend": "Needed for trend", "col_req_late": "Needed for late",
        "col_fin_trend": "Trend", "col_fin_baseline": "Baseline", "col_fin_late": "Late",
        "col_proj_own": "Proj. own", "col_proj_global": "Proj. global", "col_proj_recent": "Proj. recent",
        "col_verdict": "Verdict", "col_float_left": "Float left (d)", "col_source": "Executed from",
        "src_actual": "actual quantity", "src_inferred": "percent (inferred)",
        "col_evidence": "Evidence", "ev_thin": "thin", "ev_ok": "ok", "col_exec_days": "Days of data",
        "tile_thin": "Verdicts on thin evidence",
        "prod_unassigned": "{n} assignments carry no resource, so they cannot be trended.",
        "scurve_title": "S-curve from the file's own phasing",
        "scurve_sub": "Planned is the baseline cost the file phases by period; earned is the "
                      "file's daily spread of physical percent times baseline cost; the third "
                      "line is what the other earned-value method would say. Nothing here is "
                      "an invented distribution.",
        "scurve_planned": "Planned", "scurve_earned": "Earned", "scurve_alt": "Earned, duration method",
        "scurve_alt_physical": "Earned, physical method",
        "col_period": "Period", "col_planned_cum": "Planned cum.", "col_earned_cum": "Earned cum.",
        "col_sv": "SV cum.", "col_spi": "SPI cum.", "col_planned_pct": "Planned %",
        "col_earned_pct_cum": "Earned %", "col_alt_pct": "Other method %",
        "scurve_method": "Earned value method declared in the file: {m}.",
        "scurve_method_physical": "physical percent complete",
        "scurve_method_percent": "percent complete (duration)",
        "scurve_mixed": "Tasks in this file declare different methods; the majority rules the "
                        "curve and the mix is a finding.",
        "scurve_gap": "The two methods differ by {n} points of progress at the status date. "
                      "Switching method changes the curve, not the works.",
        "scurve_recon": "Reconciliation against the file: phasing equals baseline cost on "
                        "{a} of {c} tasks with cost; phasing to the status date equals the "
                        "file's BCWS on {b} of {t}; cost × physical equals the file's BCWP on "
                        "{e}.",
        "scurve_ahead": "{n} activities were executed ahead of their baseline window; the tool "
                        "credits nothing for them until the status date reaches the window, "
                        "the method credits them now. Worth {v}.",
        "tile_spi": "SPI", "tile_sv": "SV", "tile_planned": "Planned to date",
        "severity_view": "view",
        "conv_reconciliation": "Earned value against the file's own (matches / compared · difference · ahead of baseline window)",
        "ficha_file": "File", "ficha_leaves": "Leaf activities",
        "ficha_status": "Status date", "ficha_budget": "Baseline cost",
        "hero_label": "Accumulated physical progress",
        "hero_cap": "weighted by baseline cost, {n} activities",
        "roteiro": "Route", "index_sub": "Each line leads to its section, with the detail and "
                                          "the list of activities.",
        "view_group": "Progress by {group}", "view_group_sub": "where the money is and where "
                      "the problems are",
        "view_starts": "Starts per month", "view_starts_sub": "distribution of effort along the "
                       "contract",
        "group_intro": "Planned against actual in each group, weighted by that group's own "
                       "baseline cost. A heavy group with both bars low weighs more in the "
                       "project's risk than a light group running ahead. The table also says "
                       "how many activities of each group are marked in each check.",
        "legend_planned": "Planned", "legend_actual": "Actual",
        "col_group": "Group", "col_weight_pct": "Weight %", "col_planned_pct": "Planned %",
        "col_actual_pct": "Actual %",
        "problem": "Problem", "impact": "Impact", "solution": "Solution",
        "levar": "To reproduce in the scheduling tool", "fonte": "Where it came from:",
        "show_rows": "Show the {n} activities", "hide_rows": "Hide the activities",
        "col_pred": "Pred.", "col_succ": "Succ.", "col_service": "Service",
        "col_discipline": "Discipline", "col_section": "Section",
        "col_term_lb": "Baseline finish", "col_term": "Finish", "col_var": "Var. (d)",
        "col_float": "Float (d)", "col_real_pct": "Actual %", "col_why": "Why",
        "col_pair": "Pair", "pair_fmt": "{succ} after {pred}",
        "ignored_pairs": "{n} pairs with both activities complete were left out of the "
                         "count, by decision: they no longer change a forecast. They are in "
                         "the data file for the forensics.",
        "links_evaluated": "Relationships evaluated: {list}. Lags honoured.",
        "cycle_title": "Cycle comparison",
        "status_date": "status date",
        "not_set": "not set",
        "activities_reviewed": "activities reviewed",
        "generated": "generated",
        "print": "Print / save as PDF",
        "toggle_theme": "Toggle theme",
        "source_file": "Source file",
        "baseline_slot": "Baseline slot used",
        "budget": "Budget at completion",
        "weighted_progress": "Weighted progress",
        "threshold": "Threshold",
        "calendar_days": "calendar days",
        "physical_populated": "Physical % populated",
        "of": "of",
        "blocking": "Blocking.",
        "how_to_read": "How to read these numbers",
        "read_p1": "Progress is <b>weighted by baseline cost</b>: each activity counts for its "
                   "value, not for being one row. A positive overall figure sitting next to high "
                   "network findings usually means work executed out of the planned order, which "
                   "adds progress without meeting the plan. That is not performance.",
        "read_p2": "<b>The network findings gate everything else.</b> When the scheduling tool "
                   "recalculates over logic the works does not follow, every forecast date in the "
                   "file is derived from a false premise, so a date discussion held before "
                   "settling them is a discussion about numbers with no basis.",
        "read_p3": "Each finding below states its <b>criterion</b>, <b>where it came from</b> and "
                   "<b>how to reproduce it</b> in the scheduling tool, so nothing here has to be "
                   "taken on trust. Counts are distinct activities; a table can hold more rows "
                   "than its count when an activity is marked in two roles.",
        "index": "Index",
        "net_bad_1": "<b>Read this before any date below.</b>",
        "net_bad_2": "activities are involved in violated logic. Settle the network findings "
                     "before discussing a single date.",
        "net_good": "<b>Network integrity holds.</b> No out-of-sequence execution was found, so "
                    "the forecast dates below rest on logic the works is actually following.",
        "findings": "Findings",
        "counting_convention": "<b>Counting convention.</b>",
        "counting_tail": "Each card shows distinct activities; the tables show one row per marked "
                         "role, so a row count can legitimately exceed the card.",
        "weight_sits": "Where the weight sits",
        "weight_sub": "Grouped by {group}, ordered by share of budget. An aggregate figure means "
                      "little without this: the question is always whether the progress happened "
                      "where the money is.",
        "wbs_branch": "top WBS branch",
        "legend_budget": "share of budget at completion",
        "col_branch": "Branch", "col_activities": "Activities", "col_budget": "Budget",
        "col_weight": "Weight %", "col_earned": "Earned %", "col_findings": "Findings",
        "calendars_title": "Calendars carrying the work",
        "calendars_sub": "Every duration, variance and span in this report is counted on the "
                         "calendar of its own activity, read from that activity's Calendar "
                         "column, including that calendar's exceptions. This table is here "
                         "because it is where a construction schedule keeps its holidays and its "
                         "productivity reserve, and because a calendar registered against the "
                         "wrong year embeds optimism that nothing else in the file announces. "
                         "Read it: if the shift length or the working week is not what the works "
                         "actually does, every date below inherits the error.",
        "col_calendar": "Calendar", "col_hours_day": "Hours per day",
        "col_days_week": "Working days per week", "col_exceptions": "Exceptions",
        "col_nonworking": "Non-working exceptions",
        "distributions": "Distributions",
        "variance_title": "Finish variance against baseline",
        "variance_sub": "Bands of 30 days. The shape matters more than any single row: a mass to "
                        "the right is slippage, a mass to the left is a forecast pulled earlier, "
                        "and both tails at once is reprogramming rather than progress.",
        "float_title": "Total float",
        "float_sub": "Bands of 10 days. A large population at high float, with a contractual "
                     "milestone elapsed, usually means the milestones are not constrained in the "
                     "file.",
        "starts_title": "Activity starts per month",
        "starts_sub": "From the current schedule. A cliff of starts in one month is a plan nobody "
                      "intends to execute that way.",
        "criterion": "Criterion.",
        "came_from": "Where it came from.",
        "reproduce": "How to reproduce it.",
        "g_note": "<b>Thermometer, not a finding.</b> G says something was edited "
                  "inconsistently, not what. Use it to choose what to inspect; never report it "
                  "alone.",
        "p_note": "<b>A record defect, not an execution defect.</b> These activities are held out "
                  "of the network findings above. Without that rule a reporting problem gets "
                  "reported as an execution problem, and the conversation with the people doing "
                  "the work starts by accusing the wrong thing.",
        "counted_three": "Counted three defensible ways: {d} distinct activities, {s} as "
                         "successors, {p} as predecessors. Align with whatever convention the "
                         "other party's tool shows.",
        "conventions_title": "Conventions this report used",
        "conv_slot": "Baseline slot", "conv_chosen": "Chosen by", "conv_threshold": "Threshold",
        "conv_tolerance": "Tolerance", "conv_population": "Population",
        "conv_counting": "Network counting", "conv_working": "Working days",
        "conv_percent": "Percent source", "conv_language": "Report language",
        "conv_lang_basis": "Language chosen by",
        "group_flat": "Everything landed in a single group, so this is not a distribution. "
                      "Run the field discovery step and group by a field that actually varies, "
                      "such as discipline or work front.",
        "group_missing": "The grouping field named in the profile does not exist in this "
                         "schedule, so everything landed in one bucket. Check the name:",
        "no_activities": "No activities in this finding.",
        "no_data": "No data for this chart.",
        "showing": "Showing {n} of {total} rows; the full set is in the JSON beside this file.",
        "footer": "Generated by the <b>cronoaudit</b> skill from the schedule's own XML "
                  "export. Every finding states the filter that reproduces it, so any number "
                  "here can be checked in the source file without trusting this report. No data "
                  "left this machine.",
        # cycle report
        "cycle_read_p1": "The headline movement is <b>not necessarily progress</b>. It is the "
                         "difference between two weighted figures, and anything that changes the "
                         "basis moves it too: activities inserted or removed change the "
                         "denominator, and a rebased baseline changes the reference itself.",
        "cycle_read_p2": "So the movement is split in two: the part <b>explained</b> by "
                         "per-activity progress, and the <b>residue</b>. A residue that is not "
                         "named is where a plausible wrong number lives.",
        "prev_status": "Previous status date", "curr_status": "Current status date",
        "card_previous": "PREVIOUS", "card_current": "CURRENT", "card_movement": "MOVEMENT",
        "card_explained": "EXPLAINED", "card_residue": "RESIDUE",
        "pp_headline": "percentage points, headline", "by_progress": "by activity progress",
        "not_work": "not work done",
        "warning": "Warning.",
        "exec_or_plan": "Was it execution, or was it the plan?",
        "exec_or_plan_sub": "Three signals, read together. A forecast rewritten with no execution "
                            "behind it is legitimate, but it has to be visible as a plan change, "
                            "or the next cycle starts from a baseline nobody agreed to.",
        "card_execution": "EXECUTION", "card_replan": "REPLAN", "card_reference": "REFERENCE",
        "exec_sub": "dates moved, actuals behind them",
        "replan_sub": "dates moved, no actuals",
        "reference_sub": "the baseline itself moved",
        "baseline_moved_title": "The baseline moved — a finding about the report",
        "baseline_moved_sub": "Every deviation straddling these changes is measured against two "
                             "different references. Two figures can each be perfectly measured "
                             "and their difference still be entirely false.",
        "movement_from": "Where the movement came from",
        "movement_from_sub": "Weight-relative contributions that sum to the movement. "
                            "Denominator: {denom}.",
        "dates_moved": "Dates that moved",
        "scope_changes": "Scope changes",
        "scope_sub": "Two classes only. A renamed activity that also moved branch is "
                     "indistinguishable from a removal plus an insertion, so these are numbers to "
                     "judge rather than a classification to trust.",
        "inserted": "Inserted", "removed": "Removed",
        "col_row": "Row", "col_uid": "UID", "col_activity": "Activity", "col_wbs": "WBS",
        "col_matched": "Matched by", "col_start_moved": "Start moved",
        "col_finish_moved": "Finish moved", "col_reading": "Reading",
        "col_bl_start": "BL start moved", "col_bl_finish": "BL finish moved",
        "col_pct_prev": "% previous", "col_pct_curr": "% current",
        "col_bl_cost": "Baseline cost", "col_contribution": "Contribution pp",
        "col_role": "Role", "col_counterpart": "Counterpart", "col_link": "Link",
        "col_finish": "Finish", "col_days_elapsed": "Days elapsed",
        "col_var_cal": "Var. calendar d", "col_var_work": "Var. working d",
        "col_duration": "Duration d", "col_window": "Window wd", "col_gap": "Gap d",
        "col_actual_start": "Actual start", "col_percent": "Percent",
    },
    "pt": {
        "review_title": "Análise crítica de cronograma",
        "chip_title": "Análise crítica de cronograma",
        "reading": "Leitura",
        "profile_missing": "O perfil indica campos que este cronograma não tem:",
        "col_rate_contracted": "Ritmo contratado",
        "syn_label": "Síntese executiva",
        "syn_written": "Redigida por {who} a partir dos números deste relatório, {when}.",
        "fx_title": "Forense do cenário",
        "fx_sub": "De onde veio o atraso, por qual caminho, e quando começou? Não é apuração "
                  "contratual de atraso, que exige registro contemporâneo e método formal: é a "
                  "reconstrução do mecanismo, com evidência reproduzível, para sustentar a "
                  "reunião e a notificação.",
        "fx_paths_title": "Caminho condutor por marco",
        "fx_paths_sub": "De cada marco futuro, para trás pela predecessora que de fato empurra "
                        "cada início, até a cadeia chegar a uma atividade iniciada ou a uma "
                        "ponta aberta. A origem é a atividade mais profunda da cadeia que ainda "
                        "carrega ao menos {n} dias úteis de variação: o atraso tem nome, não "
                        "agregado.",
        "fx_origins": "Atividades que originam atraso no maior número de marcos",
        "col_milestones_n": "Marcos", "col_origin": "Origem", "col_origin_var": "Var. da origem (d)",
        "col_chain": "Cadeia", "col_open_end": "Ponta aberta", "col_reaches": "Chega a serviço iniciado",
        "col_amplifier": "Cresceu mais em", "col_added": "Acrescentou (d)",
        "fx_chain_show": "Mostrar a cadeia condutora",
        "col_via": "Via", "col_var_days": "Var. (d)", "col_started": "Iniciada",
        "fx_cal_title": "Forense de calendário",
        "fx_cal_sub": "Reserva de improdutividade cadastrada num ano enquanto as atividades "
                      "daquele calendário executam em outro embute otimismo que nada no arquivo "
                      "anuncia. Por calendário: exceções não úteis por ano contra dias de "
                      "atividade por ano.",
        "col_year": "Ano", "col_activity_days": "Dias de atividade", "col_reserve_days": "Dias de reserva",
        "col_flags": "Sinais",
        "fx_exec_title": "Padrão de execução",
        "fx_exec_sub": "Execução fora de sequência pelo mês em que a sucessora começou, e a "
                       "distribuição de escorregão de início contra a linha de base: {n} "
                       "atividades iniciadas, P50 {p50} dias, P80 {p80} dias; {early} começaram "
                       "cedo, {late} tarde.",
        "col_pairs": "Pares na contagem", "col_ignored": "Ambas concluídas, gravadas",
        "fx_cycle_title": "Este ciclo: folga consumida e movimento dos marcos",
        "fx_cycle_sub": "Entre os dois snapshots: folga consumida por grupo, atividades que "
                        "viraram críticas, e o movimento de cada marco atribuído ao que se moveu "
                        "na cadeia condutora dele: execução, replanejamento ou referência movida.",
        "col_float_before": "Folga antes", "col_float_now": "Folga agora", "col_consumed": "Consumida (d)",
        "col_moved": "Moveu (d)", "col_attribution": "Atribuição", "col_finish_before": "Término antes",
        "col_finish_now": "Término agora", "fx_became_critical": "Viraram críticas neste ciclo",
        "fc_title": "Olhando para frente",
        "fc_sub": "Cinco leituras a partir de dados que o arquivo já carrega. Earned Schedule "
                  "pergunta em que data a curva de previsto alcançou o valor agregado de hoje; "
                  "essa data, contra o tempo decorrido, dá uma eficiência de prazo e um término "
                  "independente que se compara com o do próprio cronograma, nunca o substitui. "
                  "O look-ahead diz o que as próximas semanas exigem. Os ritmos dizem onde o "
                  "praticado não alcança o necessário. As faixas de marco aplicam o escorregão "
                  "que este snapshot já mostrou. A exposição à chuva diz quanto do remanescente "
                  "cai em meses que os calendários reservam para o tempo ruim.",
        "es_title": "Earned Schedule",
        "es_es": "Earned Schedule", "es_es_cap": "data em que o plano alcançou o realizado de hoje",
        "es_sv": "SV(t)", "es_sv_cap": "dias atrás do plano, em tempo",
        "es_spi": "SPI(t)", "es_spi_cap": "eficiência de prazo até a data",
        "es_ieac": "IEAC(t)", "es_ieac_cap": "término independente nesta eficiência",
        "es_tspi": "TSPI", "es_tspi_cap": "eficiência que o restante precisa para terminar no previsto",
        "es_schedule": "Término do próprio cronograma", "es_planned": "Término previsto",
        "es_gap": "O término independente cai a {n} dias do término do próprio cronograma. A "
                  "diferença é a conversa: ou a lógica está otimista, ou o restante vai rodar "
                  "num ritmo que ainda não aconteceu.",
        "es_limits": "Limites.",
        "tspi_recoverable": "recuperável", "tspi_hard": "difícil", "tspi_unrecoverable": "irrecuperável na prática",
        "la_title": "Look-ahead", "la_window": "{w} semanas, de {a} a {b}",
        "la_start": "Devem iniciar", "la_finish": "Devem terminar", "la_planned": "Medição prevista",
        "la_projected": "No ritmo praticado", "la_reachable": "alcançável", "la_not_reachable": "não alcançável",
        "col_starts": "Inícios", "col_finishes": "Términos", "col_start": "Início",
        "rg_title": "Ritmo praticado contra necessário, por grupo",
        "rg_sub": "Percentual agregado por semana até a data, contra o percentual por semana "
                  "que o restante precisa para cair no término de linha de base do grupo. Um "
                  "número por grupo diz se dá tempo.",
        "col_practised": "Praticado %/sem", "col_required": "Necessário %/sem", "col_ratio": "Necessário ÷ praticado",
        "col_weeks_left": "Semanas restantes", "rg_on_pace": "no ritmo", "rg_stretch": "esticado", "rg_out": "fora de alcance",
        "mb_title": "Marcos com faixa de confiança",
        "mb_sub": "A distribuição de escorregão de término já observada neste snapshot, "
                  "aplicada ao término atual de cada marco futuro: P50 {a} dias, P80 {b} dias, "
                  "de {n} atividades. Não é simulação com premissa inventada.",
        "col_slip_now": "Escorregão hoje (d)", "col_p50": "P50", "col_p80": "P80", "col_deadline": "Data limite",
        "col_critical": "Crítico",
        "rx_title": "Exposição ao período chuvoso",
        "rx_sub": "Custo remanescente distribuído pela janela atual de cada atividade, lido "
                  "contra os meses que o calendário dela reserva para o tempo ruim ({rule}).",
        "rx_now": "Em meses de reserva hoje", "rx_shift": "Se tudo escorregar 30 dias",
        "col_remaining": "Remanescente", "col_in_reserve": "Em reserva", "col_share_reserve": "Parcela",
        "quality_title": "Qualidade da rede",
        "quality_sub": "Este cronograma se sustenta como modelo, antes de qualquer discussão de "
                       "data? As métricas mecânicas do modelo DCMA de 14 pontos, cada uma com "
                       "fórmula e limiar publicado, mais o que um planejador pergunta de qualquer "
                       "cronograma. É implementação das métricas, não certificação contra a norma: "
                       "os limiares vão citados para poderem ser contestados, e o que não é "
                       "computável de um arquivo é dito, não aproximado.",
        "col_metric": "Métrica", "col_count": "Qtde", "col_population": "De", "col_share": "Parcela",
        "col_threshold": "Limiar", "col_status": "Situação", "q_pass": "atende", "q_fail": "não atende",
        "q_na": "não computável", "q_info": "só contagem",
        "tile_bei": "Índice de execução da linha de base", "tile_cpli": "Índice de comprimento do caminho crítico",
        "tile_critical_n": "Atividades críticas, incompletas", "tile_open_ends": "Pontas abertas",
        "bei_cap": "{a} no prazo de {d} devidas", "cpli_cap_na": "sem data limite no marco final",
        "cpli_cap": "caminho crítico de {d} dias",
        "crit_reaches": "A cadeia crítica chega ao marco final.",
        "crit_not_reaches": "A cadeia crítica não chega ao marco final: a rede não está inteira, "
                            "ou o término está restrito em outro lugar.",
        "soft_constraints": "{n} restrições flexíveis (não antes de) também presentes; contadas, "
                            "não reprovadas.",
        "summaries_links": "{n} tarefas resumo carregam vínculo. Lógica pertence às atividades.",
        "show_items": "Mostrar os {n} itens",
        "prod_title": "Produtividade e tendência por recurso",
        "prod_sub": "As quantidades vêm das atribuições do próprio arquivo: para recurso de "
                    "material o Project guarda a quantidade nos campos de trabalho. Três ritmos "
                    "por atividade, porque um só não é leitura justa: o que esta atividade "
                    "praticou, o que o recurso praticou em todas as frentes, e os últimos {n} "
                    "dias do recurso. A projeção divide o remanescente por cada ritmo, no "
                    "calendário da própria atividade, e lê o resultado contra quatro datas.",
        "prod_verdict_intro": "Três veredictos, em ordem de gravidade. Depois da tendência mas não "
                              "depois da linha de base: reprogramar, sem atraso de linha de base. "
                              "Depois da linha de base mas não depois do término tarde: a folga "
                              "absorve, e a coluna diz quanto sobra. Depois do término tarde: a "
                              "atividade entra no caminho crítico, na data mostrada.",
        "v_ahead": "adiantada", "v_reprogram": "reprogramar",
        "v_baseline_delay": "atrasa a LB, folga absorve", "v_critical": "entra no caminho crítico",
        "v_none": "ainda sem ritmo",
        "tile_resources": "Recursos acompanhados", "tile_projected": "Atividades projetadas",
        "tile_critical": "Entrariam no caminho crítico", "tile_inferred": "Executado inferido do percentual",
        "prod_resources_title": "Ritmos por recurso",
        "col_resource": "Recurso", "col_unit": "Unid.", "col_assign": "Atrib.",
        "col_planned_qty": "Previsto", "col_exec_qty": "Executado", "col_rem_qty": "Remanescente",
        "col_rate_global": "Ritmo até a data", "col_rate_recent": "Ritmo recente", "col_rate_planned": "Ritmo previsto",
        "col_progress": "Avanço %",
        "prod_activities_title": "Atividades em andamento, projetadas",
        "col_rate_own": "Ritmo próprio", "col_req_trend": "Necessário p/ tendência", "col_req_late": "Necessário p/ tarde",
        "col_fin_trend": "Tendência", "col_fin_baseline": "Linha de base", "col_fin_late": "Tarde",
        "col_proj_own": "Proj. próprio", "col_proj_global": "Proj. global", "col_proj_recent": "Proj. recente",
        "col_verdict": "Veredicto", "col_float_left": "Folga que sobra (d)", "col_source": "Executado de",
        "src_actual": "quantidade real", "src_inferred": "percentual (inferido)",
        "col_evidence": "Evidência", "ev_thin": "fina", "ev_ok": "ok", "col_exec_days": "Dias de dado",
        "tile_thin": "Veredictos com evidência fina",
        "prod_unassigned": "{n} atribuições não têm recurso, então não podem ser tendenciadas.",
        "scurve_title": "Curva S do faseamento do próprio arquivo",
        "scurve_sub": "Previsto é o custo de linha de base que o arquivo faseia por período; "
                      "realizado é a distribuição diária de percentual físico do próprio arquivo "
                      "vezes o custo de linha de base; a terceira linha é o que o outro método "
                      "de valor agregado diria. Nada aqui é distribuição inventada.",
        "scurve_planned": "Previsto", "scurve_earned": "Realizado",
        "scurve_alt": "Realizado, método de duração",
        "scurve_alt_physical": "Realizado, método físico",
        "col_period": "Período", "col_planned_cum": "Prev. acum.", "col_earned_cum": "Real. acum.",
        "col_sv": "VP acum.", "col_spi": "IDP acum.", "col_planned_pct": "Prev %",
        "col_earned_pct_cum": "Real %", "col_alt_pct": "Outro método %",
        "scurve_method": "Método de valor agregado declarado no arquivo: {m}.",
        "scurve_method_physical": "percentual físico concluído",
        "scurve_method_percent": "percentual concluído (duração)",
        "scurve_mixed": "Tarefas deste arquivo declaram métodos diferentes; a maioria governa a "
                        "curva e a mistura é um achado.",
        "scurve_gap": "Os dois métodos diferem em {n} pontos de avanço na data de status. Trocar "
                      "o método muda a curva, não a obra.",
        "scurve_recon": "Conciliação contra o arquivo: faseamento igual ao custo de linha de base "
                        "em {a} de {c} tarefas com custo; faseamento até a data de status igual "
                        "ao BCWS do arquivo em {b} de {t}; custo × físico igual ao BCWP do "
                        "arquivo em {e}.",
        "scurve_ahead": "{n} atividades foram executadas antes da janela da linha de base; o "
                        "Project não credita nada até a data de status alcançar a janela, o "
                        "método credita agora. Valem {v}.",
        "tile_spi": "IDP", "tile_sv": "VP", "tile_planned": "Previsto até a data",
        "severity_view": "visão",
        "conv_reconciliation": "Valor agregado contra o do próprio arquivo (bate / comparadas · diferença · executadas antes da janela da linha de base)",
        "ficha_file": "Arquivo", "ficha_leaves": "Atividades folha",
        "ficha_status": "Data de status", "ficha_budget": "Custo de linha de base",
        "hero_label": "Avanço físico acumulado",
        "hero_cap": "ponderado pelo custo de linha de base, {n} atividades",
        "roteiro": "Roteiro", "index_sub": "Cada linha leva à seção correspondente, com o "
                                           "detalhamento e a lista de atividades.",
        "view_group": "Avanço por {group}", "view_group_sub": "onde está o dinheiro e onde "
                      "estão os problemas",
        "view_starts": "Partidas por mês", "view_starts_sub": "distribuição do esforço ao "
                       "longo do contrato",
        "group_intro": "Previsto contra realizado em cada grupo, ponderados pelo custo de "
                       "linha de base do próprio grupo. Um grupo de peso alto com as duas "
                       "barras baixas pesa mais no risco do projeto do que um grupo pequeno "
                       "adiantado. A tabela indica também quantas atividades de cada grupo "
                       "estão marcadas em cada verificação.",
        "legend_planned": "Previsto", "legend_actual": "Realizado",
        "col_group": "Grupo", "col_weight_pct": "Peso %", "col_planned_pct": "Prev %",
        "col_actual_pct": "Real %",
        "problem": "Problema", "impact": "Impacto", "solution": "Solução",
        "levar": "Para reproduzir no Project", "fonte": "De onde saiu:",
        "show_rows": "Mostrar as {n} atividades", "hide_rows": "Ocultar as atividades",
        "col_pred": "Pred.", "col_succ": "Suc.", "col_service": "Serviço",
        "col_discipline": "Disciplina", "col_section": "Trecho",
        "col_term_lb": "Term. LB", "col_term": "Término", "col_var": "Var (d)",
        "col_float": "Folga (d)", "col_real_pct": "Real %", "col_why": "Motivo",
        "col_pair": "Par", "pair_fmt": "{succ} depois de {pred}",
        "ignored_pairs": "{n} pares com as duas atividades concluídas ficaram fora da "
                         "contagem, por decisão: já não mudam tendência. Estão no arquivo de "
                         "dados para a forense.",
        "links_evaluated": "Vínculos avaliados: {list}. Lags respeitados.",
        "cycle_title": "Comparação de ciclo",
        "status_date": "data de status",
        "not_set": "não preenchida",
        "activities_reviewed": "atividades analisadas",
        "generated": "gerado em",
        "print": "Imprimir / salvar em PDF",
        "toggle_theme": "Alternar tema",
        "source_file": "Arquivo de origem",
        "baseline_slot": "Gaveta de linha de base usada",
        "budget": "Orçamento na conclusão",
        "weighted_progress": "Avanço ponderado",
        "threshold": "Limiar",
        "calendar_days": "dias corridos",
        "physical_populated": "% física preenchida",
        "of": "de",
        "blocking": "Impedimento.",
        "how_to_read": "Como ler estes números",
        "read_p1": "O avanço vem <b>ponderado pelo custo de linha de base</b>: cada atividade "
                   "pesa pelo seu valor, não por ser uma linha. Um número global positivo ao lado "
                   "de achados de rede altos costuma significar serviço executado fora da ordem "
                   "prevista, que soma avanço sem cumprir o previsto. Isso não é desempenho.",
        "read_p2": "<b>Os achados de rede condicionam todo o resto.</b> Quando a ferramenta "
                   "recalcula sobre uma lógica que a obra não segue, toda data de tendência do "
                   "arquivo passa a derivar de uma premissa falsa, e discutir prazo antes de "
                   "resolvê-los é discutir número sem base.",
        "read_p3": "Cada achado abaixo declara o seu <b>critério</b>, <b>de onde saiu</b> e "
                   "<b>como reproduzir</b> na ferramenta de cronograma, então nada aqui precisa "
                   "ser aceito por confiança. As contagens são de atividades distintas; uma "
                   "tabela pode ter mais linhas que a contagem quando a atividade é marcada em "
                   "dois papéis.",
        "index": "Índice",
        "net_bad_1": "<b>Leia isto antes de qualquer data abaixo.</b>",
        "net_bad_2": "atividades estão envolvidas em lógica violada. Resolva os achados de rede "
                     "antes de discutir uma única data.",
        "net_good": "<b>A integridade da rede se sustenta.</b> Não foi encontrada execução fora "
                    "de sequência, então as datas de tendência abaixo se apoiam em lógica que a "
                    "obra de fato segue.",
        "findings": "Achados",
        "counting_convention": "<b>Convenção de contagem.</b>",
        "counting_tail": "Cada cartão mostra atividades distintas; as tabelas mostram uma linha "
                         "por papel marcado, então a contagem de linhas pode legitimamente "
                         "exceder a do cartão.",
        "weight_sits": "Onde está o peso",
        "weight_sub": "Agrupado por {group}, ordenado por participação no orçamento. Um número "
                      "agregado diz pouco sem isto: a pergunta é sempre se o avanço aconteceu "
                      "onde está o dinheiro.",
        "wbs_branch": "ramo de primeiro nível da EAP",
        "legend_budget": "participação no orçamento na conclusão",
        "col_branch": "Ramo", "col_activities": "Atividades", "col_budget": "Orçamento",
        "col_weight": "Peso %", "col_earned": "Avanço %", "col_findings": "Achados",
        "calendars_title": "Calendários que carregam o trabalho",
        "calendars_sub": "Toda duração, variação e janela deste relatório é contada no calendário "
                         "da própria atividade, lido da coluna Calendário dela, incluindo as "
                         "exceções desse calendário. Esta tabela está aqui porque é onde um "
                         "cronograma de obra guarda os feriados e a reserva de improdutividade, "
                         "e porque calendário cadastrado no ano errado embute otimismo que nada "
                         "mais no arquivo anuncia. Leia: se a jornada ou a semana não é a que a "
                         "obra pratica, toda data abaixo herda o erro.",
        "col_calendar": "Calendário", "col_hours_day": "Horas por dia",
        "col_days_week": "Dias úteis por semana", "col_exceptions": "Exceções",
        "col_nonworking": "Exceções não úteis",
        "distributions": "Distribuições",
        "variance_title": "Variação de término contra a linha de base",
        "variance_sub": "Faixas de 30 dias. A forma importa mais que qualquer linha isolada: "
                        "massa à direita é escorregão, massa à esquerda é tendência puxada para "
                        "antes, e as duas caudas ao mesmo tempo é reprogramação, não avanço.",
        "float_title": "Folga total",
        "float_sub": "Faixas de 10 dias. População grande em folga alta, com marco contratual "
                     "vencido, costuma significar que os marcos não estão restritos no arquivo.",
        "starts_title": "Partidas de atividade por mês",
        "starts_sub": "Do cronograma corrente. Um paredão de partidas num único mês é um plano "
                      "que ninguém pretende executar assim.",
        "criterion": "Critério.",
        "came_from": "De onde saiu.",
        "reproduce": "Como reproduzir.",
        "g_note": "<b>Termômetro, não achado.</b> O G diz que algo foi editado de forma "
                  "inconsistente, não diz o quê. Use para escolher o que inspecionar; nunca "
                  "reporte sozinho.",
        "p_note": "<b>Defeito de registro, não de execução.</b> Estas atividades ficam fora dos "
                  "achados de rede acima. Sem essa regra, um problema de apontamento é reportado "
                  "como problema de execução, e a conversa com quem executa começa acusando a "
                  "coisa errada.",
        "counted_three": "Contado de três formas defensáveis: {d} atividades distintas, {s} como "
                         "sucessoras, {p} como predecessoras. Alinhe com a convenção que a "
                         "ferramenta da outra parte mostra.",
        "conventions_title": "Convenções que este relatório usou",
        "conv_slot": "Gaveta de linha de base", "conv_chosen": "Escolhida por",
        "conv_threshold": "Limiar", "conv_tolerance": "Tolerância",
        "conv_population": "População", "conv_counting": "Contagem de rede",
        "conv_working": "Dias úteis", "conv_percent": "Origem do percentual",
        "conv_language": "Idioma do relatório", "conv_lang_basis": "Idioma escolhido por",
        "group_flat": "Tudo caiu num único grupo, então isto não é uma distribuição. Rode a "
                      "varredura de campos e agrupe por um campo que de fato varia, como "
                      "disciplina ou frente de obra.",
        "group_missing": "O campo de agrupamento indicado no perfil não existe neste "
                         "cronograma, então tudo caiu num único grupo. Confira o nome:",
        "no_activities": "Nenhuma atividade neste achado.",
        "no_data": "Sem dados para este gráfico.",
        "showing": "Mostrando {n} de {total} linhas; o conjunto completo está no JSON ao lado "
                   "deste arquivo.",
        "footer": "Gerado pela skill <b>cronoaudit</b> a partir da exportação XML do "
                  "próprio cronograma. Cada achado declara o filtro que o reproduz, então "
                  "qualquer número aqui pode ser conferido no arquivo de origem sem confiar "
                  "neste relatório. Nenhum dado saiu desta máquina.",
        "cycle_read_p1": "O movimento de cabeçalho <b>não é necessariamente avanço</b>. É a "
                         "diferença entre dois números ponderados, e tudo que muda a base também "
                         "o move: atividades inseridas ou removidas mudam o denominador, e linha "
                         "de base reprogramada muda a própria referência.",
        "cycle_read_p2": "Então o movimento é partido em dois: a parte <b>explicada</b> pelo "
                         "avanço por atividade, e o <b>resíduo</b>. Resíduo que não é nomeado é "
                         "onde mora um número plausível e errado.",
        "prev_status": "Data de status anterior", "curr_status": "Data de status atual",
        "card_previous": "ANTERIOR", "card_current": "ATUAL", "card_movement": "MOVIMENTO",
        "card_explained": "EXPLICADO", "card_residue": "RESÍDUO",
        "pp_headline": "pontos percentuais, cabeçalho", "by_progress": "pelo avanço das atividades",
        "not_work": "não é trabalho feito",
        "warning": "Atenção.",
        "exec_or_plan": "Foi execução, ou foi o plano?",
        "exec_or_plan_sub": "Três sinais, lidos juntos. Tendência reescrita sem execução por trás "
                            "é legítima, mas precisa ficar visível como mudança de plano, ou o "
                            "ciclo seguinte parte de uma linha de base que ninguém acordou.",
        "card_execution": "EXECUÇÃO", "card_replan": "REPLANEJAMENTO",
        "card_reference": "REFERÊNCIA",
        "exec_sub": "datas mudaram, com datas reais por trás",
        "replan_sub": "datas mudaram, sem datas reais",
        "reference_sub": "a própria linha de base se moveu",
        "baseline_moved_title": "A linha de base se moveu — um achado sobre o relatório",
        "baseline_moved_sub": "Todo desvio que atravessa estas mudanças está medido contra duas "
                             "referências diferentes. Dois números podem estar perfeitamente "
                             "medidos e a diferença entre eles ser inteiramente falsa.",
        "movement_from": "De onde veio o movimento",
        "movement_from_sub": "Contribuições relativas ao peso, que somam o movimento. "
                            "Denominador: {denom}.",
        "dates_moved": "Datas que se moveram",
        "scope_changes": "Mudanças de escopo",
        "scope_sub": "Apenas duas classes. Uma atividade renomeada que também mudou de ramo é "
                     "indistinguível de uma remoção mais uma inserção, então estes são números "
                     "para julgar, não uma classificação para confiar.",
        "inserted": "Inseridas", "removed": "Removidas",
        "col_row": "Linha", "col_uid": "UID", "col_activity": "Atividade", "col_wbs": "EAP",
        "col_matched": "Casada por", "col_start_moved": "Início moveu",
        "col_finish_moved": "Término moveu", "col_reading": "Leitura",
        "col_bl_start": "Início LB moveu", "col_bl_finish": "Término LB moveu",
        "col_pct_prev": "% anterior", "col_pct_curr": "% atual",
        "col_bl_cost": "Custo linha de base", "col_contribution": "Contribuição pp",
        "col_role": "Papel", "col_counterpart": "Contraparte", "col_link": "Vínculo",
        "col_finish": "Término", "col_days_elapsed": "Dias vencidos",
        "col_var_cal": "Var. dias corridos", "col_var_work": "Var. dias úteis",
        "col_duration": "Duração d", "col_window": "Janela du", "col_gap": "Diferença d",
        "col_actual_start": "Início real", "col_percent": "Percentual",
    },
}


def ui(lang: str) -> dict:
    base = dict(UI["en"])
    base.update(UI.get(lang, {}))
    return base


# Convention sentences. They are shown to a person and must follow the report's
# language; the machine-readable keys in the findings JSON stay stable in English.
CONVENTIONS = {
    "en": {
        "slot_basis": "slot with the widest leaf-cost coverage, ties to the higher slot; "
                      "summaries and external tasks excluded",
        "threshold_unit": "working days of the activity's own calendar, between baseline "
                          "finish and current finish",
        "population": "leaf, active, non-external activities only",
        "network_counting": "both ends of each violated link are marked, to agree with the "
                            "scheduling tool's own routines",
        "working_calendar": "counted on each activity's own calendar, including its exceptions",
        "working_fallback": "NO CALENDARS IN FILE: fell back to a Monday-to-Friday "
                            "approximation, which is not a measurement",
        "percent_source": "physical percent complete when present, otherwise percent complete",
        "tolerance": "{n} day of that activity's calendar",
        "denominator": "current snapshot budget at completion",
    },
    "pt": {
        "slot_basis": "gaveta com maior cobertura de custo nas folhas, empate para a mais "
                      "alta; resumos e tarefas externas não votam",
        "threshold_unit": "dias úteis do calendário da própria atividade, entre o término da "
                          "linha de base e o término atual",
        "population": "apenas atividades folha, ativas e não externas",
        "network_counting": "as duas pontas de cada vínculo violado são marcadas, para bater "
                            "com as rotinas da própria ferramenta de cronograma",
        "working_calendar": "contados no calendário da própria atividade, incluindo as exceções "
                            "dele",
        "working_fallback": "SEM CALENDÁRIO NO ARQUIVO: caiu numa aproximação de segunda a "
                            "sexta, que não é uma medição",
        "percent_source": "percentual físico concluído quando presente, senão percentual "
                          "concluído",
        "tolerance": "{n} dia do calendário daquela atividade",
        "denominator": "orçamento na conclusão do snapshot atual",
    },
}


def conventions(lang: str) -> dict:
    base = dict(CONVENTIONS["en"])
    base.update(CONVENTIONS.get(lang, {}))
    return base


# Reasons attached to a finding row. Stable codes in the data; words here.
WHY = {
    "en": {
        "pred_not_finished": "predecessor not finished",
        "pred_finished_after_start": "predecessor finished after the successor started, beyond the lead",
        "ss_before_lag": "started before the start-to-start lag allowed",
        "ss_pred_not_started": "started while the start-to-start predecessor never started",
        "ff_before_lag": "finished before the finish-to-finish lag allowed",
        "ff_pred_not_finished": "finished while the finish-to-finish predecessor is not finished",
        "sf_before_lag": "finished before the start-to-finish lag allowed",
        "sf_pred_not_started": "finished while the start-to-finish predecessor never started",
        "start_elapsed": "start elapsed with no actual start",
        "finish_elapsed": "finish elapsed with no actual finish",
        "pending_record": "declared complete with no actual finish",
    },
    "pt": {
        "pred_not_finished": "predecessora não terminou",
        "pred_finished_after_start": "predecessora terminou depois do início da sucessora, além do lead",
        "ss_before_lag": "começou antes do que o lag início-início permite",
        "ss_pred_not_started": "começou com a predecessora início-início sem começar",
        "ff_before_lag": "terminou antes do que o lag término-término permite",
        "ff_pred_not_finished": "terminou com a predecessora término-término sem terminar",
        "sf_before_lag": "terminou antes do que o lag início-término permite",
        "sf_pred_not_started": "terminou com a predecessora início-término sem começar",
        "start_elapsed": "início vencido sem início real",
        "finish_elapsed": "término vencido sem término real",
        "pending_record": "declarada concluída sem término real",
    },
}


def why(lang: str, code: str) -> str:
    return WHY.get(lang, WHY["en"]).get(code, code)


# Network quality metrics: title, what it measures, the formula in words. The
# thresholds are quoted in the data, not here, so the numbers stay in one place.
QUALITY = {
    "en": {
        "Q1": ("Missing logic", "Incomplete activities with no predecessor or no successor. An open end is delay that does not propagate."),
        "Q2": ("Leads", "Links with a negative lag. A lead hides an overlap the logic should model explicitly."),
        "Q3": ("Lags", "Links with a positive lag. Lag is time nobody owns; a waiting activity is honest about it."),
        "Q4": ("Relationship types", "Links that are not finish-to-start. Not wrong, but each one deserves a reason."),
        "Q5": ("Hard constraints", "Incomplete activities pinned by a must-start, must-finish or no-later-than constraint. A pinned date fights the logic."),
        "Q6": ("High float", "Incomplete activities with more than 44 working days of total float. Usually a milestone nobody constrained."),
        "Q7": ("Negative float", "Incomplete activities with total float below zero: a date the logic cannot meet."),
        "Q8": ("High duration", "Incomplete activities with more than 44 working days remaining. Too coarse to control."),
        "Q9": ("Invalid dates", "Actual dates after the status date. Forecast dates in the past are the H finding above."),
        "Q10": ("No resource", "Incomplete activities with duration and no assignment. Nothing to trend."),
        "Q11": ("Missed activities", "Due to finish by the status date on the baseline and not finished on time."),
        "Q12": ("Critical path test", "Requires perturbing the schedule and watching the finish move. Not computable from a file."),
        "Q13": ("Critical path length index", "Meaningful only with a deadline on the finish milestone; without one it is 1.0 by construction."),
        "Q14": ("Baseline execution index", "Activities finished on time divided by activities due by the status date."),
    },
    "pt": {
        "Q1": ("Lógica ausente", "Atividades incompletas sem predecessora ou sem sucessora. Ponta aberta é atraso que não propaga."),
        "Q2": ("Leads", "Vínculos com lag negativo. Lead esconde sobreposição que a lógica deveria modelar explicitamente."),
        "Q3": ("Lags", "Vínculos com lag positivo. Lag é tempo sem dono; uma atividade de espera é honesta sobre isso."),
        "Q4": ("Tipos de vínculo", "Vínculos que não são término-início. Não é erro, mas cada um merece um motivo."),
        "Q5": ("Restrições rígidas", "Atividades incompletas presas por restrição de deve iniciar, deve terminar ou não depois de. Data presa briga com a lógica."),
        "Q6": ("Folga alta", "Atividades incompletas com mais de 44 dias úteis de folga total. Normalmente marco que ninguém restringiu."),
        "Q7": ("Folga negativa", "Atividades incompletas com folga total abaixo de zero: data que a lógica não alcança."),
        "Q8": ("Duração longa", "Atividades incompletas com mais de 44 dias úteis remanescentes. Grossas demais para controlar."),
        "Q9": ("Datas inválidas", "Datas reais depois da data de status. Datas de tendência no passado são o achado H acima."),
        "Q10": ("Sem recurso", "Atividades incompletas com duração e nenhuma atribuição. Nada para tendenciar."),
        "Q11": ("Atividades perdidas", "Deviam terminar até a data de status pela linha de base e não terminaram no prazo."),
        "Q12": ("Teste de caminho crítico", "Exige perturbar o cronograma e ver o término mover. Não é computável de um arquivo."),
        "Q13": ("Índice de comprimento do caminho crítico", "Só faz sentido com data limite no marco final; sem ela é 1,0 por construção."),
        "Q14": ("Índice de execução da linha de base", "Atividades terminadas no prazo divididas pelas devidas até a data de status."),
    },
}


def quality_text(lang: str) -> dict:
    return QUALITY.get(lang, QUALITY["en"])
