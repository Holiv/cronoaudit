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
        "severity_view": "view",
        "conv_reconciliation": "Earned value against the file's own (matches / compared · difference)",
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
        "footer": "Generated by the <b>schedule-integrity</b> skill from the schedule's own XML "
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
        "severity_view": "visão",
        "conv_reconciliation": "Valor agregado contra o do próprio arquivo (bate / comparadas · diferença)",
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
        "footer": "Gerado pela skill <b>schedule-integrity</b> a partir da exportação XML do "
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
