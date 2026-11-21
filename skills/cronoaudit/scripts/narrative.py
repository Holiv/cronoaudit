#!/usr/bin/env python3
"""Readings: the sentences a planner would say about these numbers.

Deterministic, rule-based, in the report's language. Each reading is built from
the payload's own figures, so it says what the data supports and nothing more --
and when a figure is missing the sentence is simply not produced. This is the
layer that lets the report be handed to somebody with no presenter.

The executive synthesis is a different thing: prose written by whoever runs the
skill, with the figures in hand, and injected into the report under its own
label. See `inject_narrative.py`.
"""
from __future__ import annotations

R = {
    "en": {
        "net_hold": "The network holds: no out-of-sequence execution, so the forecast dates rest on logic the works follows.",
        "net_broken": "{n} activities sit in violated logic ({a1} out of sequence, {a2} in total inversion). Every forecast date below is derived from a network the works does not follow; settle these before discussing a date.",
        "progress": "Weighted progress is {e}% against {p}% planned: {d} points behind.",
        "progress_ahead": "Weighted progress is {e}% against {p}% planned: {d} points ahead.",
        "recon_ok": "The skill's earned value matched the file's own on {m} of {c} leaves to the cent; the difference is explained.",
        "recon_gap": "The skill's earned value differs from the file's on {u} leaves without explanation; check the baseline slot and the earned-value method before trusting either figure.",
        "spi": "Cumulative SPI is {s}: the works has earned {pct}% of what the plan expected by now.",
        "method_gap": "The other earned-value method would read {alt}% instead of {e}%, a gap of {g} points. Switching method changes the curve, not the works.",
        "earned_before_plan": "{v} ({pct}% of the baseline cost) was earned before the first planned day, {d}: execution ahead of its baseline window, which the tool credits only when the status date reaches the window.",
        "weight_top": "{g} carries {w}% of the budget and stands at {e}% earned against {p}% planned.",
        "weight_behind": "{n} groups are more than {d} points behind their own plan; the largest is {g}.",
        "weight_flat": "Everything sits in one group, so the weight distribution says nothing yet; group by a discovered field.",
        "prod_solid": "Of {n} activities in progress with a trend, {s} rest on solid evidence: {ahead} ahead, {rep} to reprogram, {abs} with the baseline missed and the float absorbing it, {crit} that would enter the critical path.",
        "prod_thin": "{t} projections rest on thin evidence or a percent-derived quantity; read them as questions, not verdicts.",
        "rate_falling": "{r} is slowing: planned {p} a day, {g} practised to date, {rc} in the last thirty days.",
        "q_fail": "The network fails {n} of the quantitative metrics: {list}.",
        "q_pass_all": "The network passes every quantitative metric with a threshold.",
        "bei": "Of {d} activities due by the status date, {a} finished on time: a baseline execution index of {b}.",
        "float_deadline": "{f}% of incomplete activities carry more than 44 working days of float while {m} of {mm} milestones have no deadline: the float is not slack, it is an unconstrained plan.",
        "es_behind": "Earned Schedule falls on {es}: the plan reached today's earned value {d} days ago, a schedule efficiency SPI(t) of {spi}.",
        "es_ahead": "Earned Schedule falls on {es}, {d} days ahead of today: SPI(t) {spi}.",
        "es_ieac": "At this efficiency the independent finish is {ieac}, {gap} days from the schedule's own {sched}. Either the logic is optimistic or the remainder will run at a pace not yet seen.",
        "es_tspi_easy": "TSPI is {t}: the remainder can finish on the planned date at the plan's own pace.",
        "es_tspi_hard": "TSPI is {t}: the remainder must run {pct}% above the plan to finish on the planned date. Modest because most of the duration is still ahead, not because the lag is small.",
        "es_tspi_no": "TSPI is {t}: the remainder would need {pct}% above the plan, which the literature treats as unrecoverable in practice.",
        "la_no": "The next {w} weeks plan {p}% of earning; the practised rate delivers {q}%. Not reachable without a change of pace.",
        "la_yes": "The next {w} weeks plan {p}% of earning and the practised rate delivers {q}%: reachable.",
        "rg_out": "{n} groups cannot reach their baseline finish at the practised pace; {g} needs {r}× its current rate.",
        "rg_ok": "Every group with a trend is on pace or within a stretch of its baseline finish.",
        "rain": "{s}% of the remaining cost sits in months the calendars reserve for bad weather, {t}% if everything slips thirty days.",
        "fx_origins": "{o} of {m} future milestones trace to a named origin; activity {id} originates delay on {k} of them.",
        "fx_none": "No future milestone carries variance above the threshold, so no origin is named.",
        "fx_cal": "Calendar forensics flags {n} calendars: {list}.",
        "fx_oos_rising": "Out-of-sequence execution is rising, from {a} pairs a month to {b}: the practice is accelerating.",
        "fx_oos_falling": "Out-of-sequence execution is falling, from {a} pairs a month to {b}.",
        "fx_slip": "Of {n} started activities, {early} started early and {late} late; the median start was {p50} days {dir} the baseline.",
        "early": "before", "late": "after",
        "syn_label": "Executive synthesis",
        "syn_written": "Written by {who} from the figures in this report, on {when}.",
    },
    "pt": {
        "net_hold": "A rede se sustenta: não há execução fora de sequência, então as datas de tendência se apoiam em lógica que a obra segue.",
        "net_broken": "{n} atividades estão em lógica violada ({a1} fora de sequência, {a2} em inversão total). Toda data de tendência abaixo deriva de uma rede que a obra não segue; resolva isso antes de discutir uma data.",
        "progress": "O avanço ponderado é {e}% contra {p}% previsto: {d} pontos atrás.",
        "progress_ahead": "O avanço ponderado é {e}% contra {p}% previsto: {d} pontos à frente.",
        "recon_ok": "O valor agregado da skill bateu com o do arquivo em {m} de {c} folhas ao centavo; a diferença está explicada.",
        "recon_gap": "O valor agregado da skill difere do arquivo em {u} folhas sem explicação; confira a gaveta de linha de base e o método antes de confiar em qualquer dos dois.",
        "spi": "O IDP acumulado é {s}: a obra agregou {pct}% do que o plano esperava até agora.",
        "method_gap": "O outro método de valor agregado leria {alt}% em vez de {e}%, diferença de {g} pontos. Trocar o método muda a curva, não a obra.",
        "earned_before_plan": "{v} ({pct}% do custo de linha de base) foi agregado antes do primeiro dia previsto, {d}: execução antes da janela de linha de base, que a ferramenta só credita quando a data de status alcança a janela.",
        "weight_top": "{g} carrega {w}% do orçamento e está em {e}% realizado contra {p}% previsto.",
        "weight_behind": "{n} grupos estão mais de {d} pontos atrás do próprio previsto; o maior é {g}.",
        "weight_flat": "Tudo está num único grupo, então a distribuição de peso ainda não diz nada; agrupe por um campo descoberto.",
        "prod_solid": "Das {n} atividades em andamento com tendência, {s} se apoiam em evidência sólida: {ahead} adiantadas, {rep} para reprogramar, {abs} com a linha de base perdida e a folga absorvendo, {crit} que entrariam no caminho crítico.",
        "prod_thin": "{t} projeções se apoiam em evidência fina ou em quantidade derivada de percentual; leia como pergunta, não como veredicto.",
        "rate_falling": "{r} está desacelerando: previsto {p} por dia, {g} praticado até a data, {rc} nos últimos trinta dias.",
        "q_fail": "A rede não atende {n} das métricas quantitativas: {list}.",
        "q_pass_all": "A rede atende todas as métricas quantitativas com limiar.",
        "bei": "De {d} atividades devidas até a data de status, {a} terminaram no prazo: índice de execução da linha de base de {b}.",
        "float_deadline": "{f}% das atividades incompletas carregam mais de 44 dias úteis de folga enquanto {m} de {mm} marcos não têm data limite: a folga não é margem, é plano sem restrição.",
        "es_behind": "O Earned Schedule cai em {es}: o plano alcançou o realizado de hoje há {d} dias, eficiência de prazo SPI(t) de {spi}.",
        "es_ahead": "O Earned Schedule cai em {es}, {d} dias à frente de hoje: SPI(t) {spi}.",
        "es_ieac": "Nesta eficiência o término independente é {ieac}, a {gap} dias do término do próprio cronograma, {sched}. Ou a lógica está otimista, ou o restante vai rodar num ritmo que ainda não aconteceu.",
        "es_tspi_easy": "O TSPI é {t}: o restante termina na data prevista no ritmo do próprio plano.",
        "es_tspi_hard": "O TSPI é {t}: o restante precisa rodar {pct}% acima do plano para terminar na data prevista. Modesto porque quase toda a duração ainda está pela frente, não porque o atraso seja pequeno.",
        "es_tspi_no": "O TSPI é {t}: o restante precisaria de {pct}% acima do plano, o que a literatura trata como irrecuperável na prática.",
        "la_no": "As próximas {w} semanas preveem {p}% de medição; o ritmo praticado entrega {q}%. Não alcançável sem mudança de ritmo.",
        "la_yes": "As próximas {w} semanas preveem {p}% de medição e o ritmo praticado entrega {q}%: alcançável.",
        "rg_out": "{n} grupos não alcançam o término de linha de base no ritmo praticado; {g} precisa de {r}× o ritmo atual.",
        "rg_ok": "Todo grupo com tendência está no ritmo ou a um esforço do término de linha de base.",
        "rain": "{s}% do custo remanescente cai em meses que os calendários reservam para tempo ruim, {t}% se tudo escorregar trinta dias.",
        "fx_origins": "{o} de {m} marcos futuros têm origem nomeada; a atividade {id} origina atraso em {k} deles.",
        "fx_none": "Nenhum marco futuro carrega variação acima do limiar, então nenhuma origem é nomeada.",
        "fx_cal": "A forense de calendário sinaliza {n} calendários: {list}.",
        "fx_oos_rising": "A execução fora de sequência está subindo, de {a} pares por mês para {b}: a prática está acelerando.",
        "fx_oos_falling": "A execução fora de sequência está caindo, de {a} pares por mês para {b}.",
        "fx_slip": "De {n} atividades iniciadas, {early} começaram cedo e {late} tarde; o início mediano foi {p50} dias {dir} da linha de base.",
        "early": "antes", "late": "depois",
        "syn_label": "Síntese executiva",
        "syn_written": "Redigida por {who} a partir dos números deste relatório, em {when}.",
    },
}


def _n(v, d=1):
    if v is None:
        return "—"
    return f"{v:,.{d}f}" if isinstance(v, float) else f"{v:,}"


def build(payload: dict, lang: str) -> dict:
    T = R.get(lang, R["en"])
    m = payload.get("meta") or {}
    out: dict[str, list] = {}

    def add(section, key, **kw):
        try:
            out.setdefault(section, []).append(T[key].format(**kw))
        except (KeyError, ValueError, TypeError):
            pass

    # ---- verdict
    f = {x["code"]: x for x in payload.get("findings", [])}
    net = (f.get("A1", {}).get("count") or 0) + (f.get("A2", {}).get("count") or 0)
    if net:
        add("verdict", "net_broken", n=_n(net, 0), a1=_n(f["A1"]["count"], 0), a2=_n(f["A2"]["count"], 0))
    else:
        add("verdict", "net_hold")
    e, p = m.get("percent_earned"), m.get("percent_planned_file")
    if e is not None and p is not None:
        add("verdict", "progress_ahead" if e > p else "progress", e=_n(e, 2), p=_n(p, 2), d=_n(abs(e - p), 2))
    rc = m.get("reconciliation") or {}
    if rc.get("leaves_compared"):
        if rc.get("unexplained"):
            add("verdict", "recon_gap", u=_n(rc["unexplained"], 0))
        else:
            add("verdict", "recon_ok", m=_n(rc["matches_to_cent"], 0), c=_n(rc["leaves_compared"], 0))

    # ---- S-curve
    s = payload.get("scurve") or {}
    T_ = s.get("totals") or {}
    if T_.get("spi") is not None:
        add("scurve", "spi", s=_n(T_["spi"], 3), pct=_n(T_["spi"] * 100, 1))
    if T_.get("method_gap_points") is not None and T_.get("earned_alt_pct") is not None:
        add("scurve", "method_gap", alt=_n(T_["earned_alt_pct"], 2), e=_n(T_.get("earned_pct"), 2),
            g=_n(abs(T_["method_gap_points"]), 2))
    periods = s.get("periods") or []
    first_planned = next((p["period"] for p in periods if (p.get("planned") or 0) > 0), None)
    if first_planned:
        before = sum((p.get("earned") or 0) for p in periods if p["period"] < first_planned)
        if before > 0 and s.get("bac"):
            add("scurve", "earned_before_plan", v=_n(before, 0), pct=_n(before / s["bac"] * 100, 2),
                d=first_planned)

    # ---- groups
    g = (payload.get("charts") or {}).get("by_group") or []
    if m.get("grouping_uninformative"):
        add("groups", "weight_flat")
    elif g:
        top = g[0]
        add("groups", "weight_top", g=top["label"], w=_n(top["weight_pct"], 1),
            e=_n(top["earned_pct"], 1), p=_n(top["planned_pct"], 1))
        behind = [r for r in g if (r["planned_pct"] or 0) - (r["earned_pct"] or 0) > 5]
        if behind:
            add("groups", "weight_behind", n=_n(len(behind), 0), d=5,
                g=max(behind, key=lambda r: r["weight_pct"])["label"])

    # ---- productivity
    pr = payload.get("productivity") or {}
    S = pr.get("summary") or {}
    acts = pr.get("activities") or []
    if acts:
        solid = [a for a in acts if not a.get("thin_evidence")]
        cnt = lambda v: sum(1 for a in solid if a.get("verdict_global") == v)
        add("productivity", "prod_solid", n=_n(len(acts), 0), s=_n(len(solid), 0), ahead=_n(cnt("ahead"), 0),
            rep=_n(cnt("reprogram"), 0), abs=_n(cnt("baseline_delay"), 0), crit=_n(cnt("critical"), 0))
        if S.get("thin_evidence"):
            add("productivity", "prod_thin", t=_n(S["thin_evidence"], 0))
    for r in (pr.get("resources") or [])[:3]:
        if r.get("rate_planned") and r.get("rate_global") and r.get("rate_recent") and \
                r["rate_recent"] < r["rate_global"] < r["rate_planned"]:
            add("productivity", "rate_falling", r=r["name"], p=_n(r["rate_planned"], 0),
                g=_n(r["rate_global"], 0), rc=_n(r["rate_recent"], 0))

    # ---- quality
    q = payload.get("quality") or {}
    fails = [x for x in q.get("metrics", []) if x.get("status") == "fail"]
    if q.get("metrics"):
        if fails:
            add("quality", "q_fail", n=_n(len(fails), 0), list=", ".join(f"{x['code']} {x.get('title','')}" for x in fails))
        else:
            add("quality", "q_pass_all")
    I = q.get("indices") or {}
    if I.get("bei") is not None:
        add("quality", "bei", d=_n(I["bei_due"], 0), a=_n(I["bei_on_time"], 0), b=_n(I["bei"], 2))
    q6 = next((x for x in q.get("metrics", []) if x["code"] == "Q6"), None)
    QL = q.get("qualitative") or {}
    if q6 and q6.get("share_pct") and QL.get("milestones"):
        add("quality", "float_deadline", f=_n(q6["share_pct"], 0), m=_n(QL.get("milestones_without_deadline"), 0), mm=_n(QL["milestones"], 0))

    # ---- forecast
    fc = payload.get("forecast") or {}
    E = fc.get("earned_schedule") or {}
    if E.get("available"):
        if E["sv_t_days"] < 0:
            add("forecast", "es_behind", es=E["es_date"], d=_n(abs(E["sv_t_days"]), 0), spi=_n(E["spi_t"], 3))
        else:
            add("forecast", "es_ahead", es=E["es_date"], d=_n(E["sv_t_days"], 0), spi=_n(E["spi_t"], 3))
        if E.get("ieac_t_date") and E.get("gap_vs_schedule_days") is not None:
            add("forecast", "es_ieac", ieac=E["ieac_t_date"], gap=_n(abs(E["gap_vs_schedule_days"]), 0), sched=E.get("schedule_finish"))
        if E.get("tspi") is not None:
            key = {"recoverable": "es_tspi_easy", "hard": "es_tspi_hard", "unrecoverable": "es_tspi_no"}.get(E.get("tspi_verdict"), "es_tspi_hard")
            add("forecast", key, t=_n(E["tspi"], 3), pct=_n(max(0.0, (E["tspi"] - 1) * 100), 1))
    for w in fc.get("lookahead") or []:
        if w.get("reachable") is not None:
            add("forecast", "la_yes" if w["reachable"] else "la_no", w=w["weeks"], p=_n(w["planned_earning_pct"], 2), q=_n(w["projected_pct"], 2))
            break
    rg = [r for r in fc.get("rates_by_group") or [] if r.get("verdict") == "out of reach"]
    if fc.get("rates_by_group"):
        if rg:
            worst = max(rg, key=lambda r: r.get("ratio_required_over_practised") or 0)
            add("forecast", "rg_out", n=_n(len(rg), 0), g=worst["group"], r=_n(worst["ratio_required_over_practised"], 1))
        else:
            add("forecast", "rg_ok")
    RX = fc.get("rain_exposure") or {}
    if RX.get("share_in_reserve_pct") is not None:
        add("forecast", "rain", s=_n(RX["share_in_reserve_pct"], 0), t=_n(RX.get("share_if_slips_30_days_pct"), 0))

    # ---- forensics
    fx = payload.get("forensics") or {}
    FS = fx.get("summary") or {}
    if FS.get("milestones"):
        if FS.get("with_origin") and FS.get("origins"):
            o = FS["origins"][0]
            add("forensics", "fx_origins", o=_n(FS["with_origin"], 0), m=_n(FS["milestones"], 0), id=o["id"], k=_n(o["milestones"], 0))
        else:
            add("forensics", "fx_none")
    flagged = [c for c in fx.get("calendars") or [] if c.get("flags")]
    if flagged:
        add("forensics", "fx_cal", n=_n(len(flagged), 0), list="; ".join(f"{c['name']}: {', '.join(c['flags'])}" for c in flagged[:3]))
    oos = (fx.get("execution") or {}).get("out_of_sequence_by_month") or []
    oos = [x for x in oos if x.get("pairs")]
    if len(oos) >= 3:
        a, b = oos[0]["pairs"], oos[-1]["pairs"]
        if b > a * 1.5:
            add("forensics", "fx_oos_rising", a=_n(a, 0), b=_n(b, 0))
        elif a > b * 1.5:
            add("forensics", "fx_oos_falling", a=_n(a, 0), b=_n(b, 0))
    SL = (fx.get("execution") or {}).get("start_slippage") or {}
    if SL.get("sample"):
        p50 = SL.get("p50") or 0
        add("forensics", "fx_slip", n=_n(SL["sample"], 0), early=_n(SL["started_early"], 0), late=_n(SL["started_late"], 0),
            p50=_n(abs(p50), 0), dir=T["early"] if p50 < 0 else T["late"])
    return out


# ---------------------------------------------------------------------------
# The cycle comparison. Same contract as above: every sentence is built from the
# comparison's own figures, and a figure that is missing produces no sentence.
# ---------------------------------------------------------------------------
RC = {
    "en": {
        "mv": "Weighted progress went from {a}% to {b}%: {m} points. Per-activity progress explains {x} of them and {r} are not explained by work done.",
        "mv_clean": "Weighted progress went from {a}% to {b}%: {m} points, all of it explained by per-activity progress.",
        "tr": "{e} activities moved their dates with actual dates behind them and {r} with none; the baseline itself moved on {b}.",
        "tr_none": "No activity moved its dates between the two deliveries.",
        "sc": "{i} activities inserted and {r} removed.",
        "sc_none": "No activity was inserted or removed: the scope is the same in both deliveries.",
        "fin_later": "The project finish moved from {a} to {b}: {d} calendar days later.",
        "fin_earlier": "The project finish moved from {a} to {b}: {d} calendar days earlier.",
        "fin_same": "The project finish did not move: {b} in both deliveries.",
        "fin_driver": "What holds the current date is row {id}, {name}, finishing on {f}. This is an approximation: the last-finishing open activity, walked back through the predecessor that lands latest; the network was not recalculated.",
        "fin_driver_flag_no": "The tool does not flag that row as critical, so read the path before quoting it.",
        "fin_driver_changed": "In the previous delivery the date was held by another activity (row {id}, {name}): the path that drives the finish changed.",
        "fin_driver_same": "The same activity held the date in the previous delivery.",
        "cp": "{e} activities entered the critical path and {l} left it, {lc} of those by finishing. Critical now: {n}, against {p} before.",
        "cp_none": "No activity entered or left the critical path. Critical now: {n}, against {p} before.",
        "cp_inserted": "{n} of the activities inserted this cycle are critical; they are listed under scope.",
        "cp_fell": "{n} unfinished activities lost a working day of float or more; the largest loss is {d} days, on row {id}.",
        "cp_fell_none": "No unfinished activity lost a working day of float or more.",
        "cp_basis_flag": "Read by the tool's own Critical flag.",
        "cp_basis_float": "The files carry no Critical flag, so critical here means total float at or below zero.",
        "cp_basis_mixed": "The two deliveries could not be read by the same criterion (one carries the Critical flag, the other does not); treat entries and exits with care.",
        "lg": "{a} links added, {r} removed, {l} with the lag changed and {t} with the type changed, between activities present in both deliveries.",
        "lg_none": "No link between activities present in both deliveries was edited.",
        "lg_scope": "A further {n} links hang on inserted or removed activities: scope, not edited logic.",
        "lg_con": "Constraints on unfinished activities: {a} added, {c} changed and {r} removed.",
        "lg_con_none": "No constraint was added, changed or removed.",
        "lg_hard": "{n} of them are now hard (must start or finish on, or no later than): the date is pinned and the network stops deciding it.",
        "du": "{n} activities with no actual start in either delivery had their duration edited: {up} longer and {down} shorter, a net {net} working days. Nothing was executed on them; this is the plan rewritten.",
        "du_none": "No activity had its duration edited before starting.",
        "pr": "The past was rewritten on {n} activities: {s} actual starts and {f} actual finishes changed, and {p} percents complete went down.",
        "pr_removed": "{n} actual dates were withdrawn altogether: work reported as started or finished last cycle is no longer recorded as such.",
        "pr_time": "{n} of the date changes stay within the same day (time of day only); they are listed last and weigh less.",
        "pr_ask": "Every figure the previous cycle reported on these activities rested on a record that no longer exists. Ask for each correction to be stated.",
        "pr_none": "No actual date changed and no percent complete went down: the past reads the same in both deliveries.",
        "ql": "Of the {t} metrics computable in both deliveries, {w} worsened, {i} improved and {u} did not move.",
        "ql_bad": "Went from pass to fail: {list}.",
        "ql_good": "Went from fail to pass: {list}.",
        "ql_bei": "Baseline execution index: {a} before, {b} now.",
    },
    "pt": {
        "mv": "O avanço ponderado foi de {a}% para {b}%: {m} pontos. O avanço por atividade explica {x} deles e {r} não são explicados por trabalho feito.",
        "mv_clean": "O avanço ponderado foi de {a}% para {b}%: {m} pontos, todos explicados pelo avanço por atividade.",
        "tr": "{e} atividades moveram datas com datas reais por trás e {r} sem nenhuma; a própria linha de base se moveu em {b}.",
        "tr_none": "Nenhuma atividade moveu datas entre as duas entregas.",
        "sc": "{i} atividades inseridas e {r} removidas.",
        "sc_none": "Nenhuma atividade foi inserida ou removida: o escopo é o mesmo nas duas entregas.",
        "fin_later": "O término do projeto foi de {a} para {b}: {d} dias corridos mais tarde.",
        "fin_earlier": "O término do projeto foi de {a} para {b}: {d} dias corridos mais cedo.",
        "fin_same": "O término do projeto não se moveu: {b} nas duas entregas.",
        "fin_driver": "O que segura a data atual é a linha {id}, {name}, com término em {f}. É uma aproximação: a atividade em aberto que termina por último, percorrida para trás pela predecessora que chega mais tarde; a rede não foi recalculada.",
        "fin_driver_flag_no": "A ferramenta não marca essa linha como crítica, então leia o caminho antes de citá-lo.",
        "fin_driver_changed": "Na entrega anterior a data era segurada por outra atividade (linha {id}, {name}): o caminho que conduz o término mudou.",
        "fin_driver_same": "A mesma atividade segurava a data na entrega anterior.",
        "cp": "{e} atividades entraram no caminho crítico e {l} saíram, {lc} delas por terem sido concluídas. Críticas agora: {n}, contra {p} antes.",
        "cp_none": "Nenhuma atividade entrou ou saiu do caminho crítico. Críticas agora: {n}, contra {p} antes.",
        "cp_inserted": "{n} das atividades inseridas neste ciclo são críticas; estão listadas em escopo.",
        "cp_fell": "{n} atividades não concluídas perderam um dia útil de folga ou mais; a maior perda é de {d} dias, na linha {id}.",
        "cp_fell_none": "Nenhuma atividade não concluída perdeu um dia útil de folga ou mais.",
        "cp_basis_flag": "Lido pelo próprio campo Crítica da ferramenta.",
        "cp_basis_float": "Os arquivos não trazem o campo Crítica, então crítica aqui significa folga total menor ou igual a zero.",
        "cp_basis_mixed": "As duas entregas não puderam ser lidas pelo mesmo critério (uma traz o campo Crítica, a outra não); trate entradas e saídas com cuidado.",
        "lg": "{a} vínculos incluídos, {r} removidos, {l} com a latência alterada e {t} com o tipo alterado, entre atividades presentes nas duas entregas.",
        "lg_none": "Nenhum vínculo entre atividades presentes nas duas entregas foi editado.",
        "lg_scope": "Outros {n} vínculos estão em atividades inseridas ou removidas: é escopo, não lógica editada.",
        "lg_con": "Restrições em atividades não concluídas: {a} incluídas, {c} alteradas e {r} removidas.",
        "lg_con_none": "Nenhuma restrição foi incluída, alterada ou removida.",
        "lg_hard": "{n} delas agora são rígidas (deve iniciar ou terminar em, ou não depois de): a data fica presa e a rede deixa de decidi-la.",
        "du": "{n} atividades sem início real em nenhuma das entregas tiveram a duração editada: {up} mais longas e {down} mais curtas, saldo de {net} dias úteis. Nada foi executado nelas; é o plano reescrito.",
        "du_none": "Nenhuma atividade teve a duração editada antes de iniciar.",
        "pr": "O passado foi reescrito em {n} atividades: {s} inícios reais e {f} términos reais mudaram, e {p} percentuais concluídos caíram.",
        "pr_removed": "{n} datas reais foram retiradas por completo: trabalho informado como iniciado ou concluído no ciclo anterior não está mais registrado assim.",
        "pr_time": "{n} das mudanças de data ficam dentro do mesmo dia (só o horário); estão listadas por último e pesam menos.",
        "pr_ask": "Todo número que o ciclo anterior informou sobre essas atividades se apoiava num registro que não existe mais. Peça que cada correção seja declarada.",
        "pr_none": "Nenhuma data real mudou e nenhum percentual concluído caiu: o passado lê igual nas duas entregas.",
        "ql": "Das {t} métricas calculáveis nas duas entregas, {w} pioraram, {i} melhoraram e {u} não se moveram.",
        "ql_bad": "Passaram de atende para não atende: {list}.",
        "ql_good": "Passaram de não atende para atende: {list}.",
        "ql_bei": "Índice de execução da linha de base: {a} antes, {b} agora.",
    },
}

HARD_CONSTRAINT_CODES = {"MSO", "MFO", "SNLT", "FNLT"}


def fnum(v, d, lang):
    """A number the way the report's language writes it; never a negative zero."""
    if v is None:
        return "—"
    v = round(float(v), d)
    if v == 0:
        v = 0.0
    s = f"{v:,.{d}f}"
    if lang == "pt":
        s = s.replace(",", " ").replace(".", ",").replace(" ", ".")
    return s


def build_cycle(cmp_res: dict, lang: str, fmt_date, metric_title=None) -> dict:
    """Readings for the cycle report, keyed by section.

    `fmt_date` is the report's own date formatter, passed in so the sentences and
    the tables cannot disagree on how a date is written.
    """
    T = RC.get(lang, RC["en"])
    out: dict[str, list] = {}

    def add(section, key, **kw):
        try:
            out.setdefault(section, []).append(T[key].format(**kw))
        except (KeyError, ValueError, TypeError):
            pass

    def i(v):
        return fnum(v, 0, lang)

    # ---- movement, trend, scope
    prev, curr = cmp_res.get("previous") or {}, cmp_res.get("current") or {}
    mv, gap = cmp_res.get("movement_points"), cmp_res.get("movement_unexplained_points")
    if mv is not None:
        args = dict(a=fnum(prev.get("percent_earned"), 2, lang),
                    b=fnum(curr.get("percent_earned"), 2, lang), m=fnum(mv, 2, lang),
                    x=fnum(cmp_res.get("decomposition_sums_to_points"), 2, lang),
                    r=fnum(gap, 2, lang))
        add("movement", "mv" if abs(gap or 0) >= 0.01 else "mv_clean", **args)
    trend = cmp_res.get("trend") or []
    e = sum(1 for t in trend if t["reading"] == "execution")
    r = sum(1 for t in trend if t["reading"] == "replan")
    b = len(cmp_res.get("baseline_moved") or [])
    if e or r or b:
        add("trend", "tr", e=i(e), r=i(r), b=i(b))
    else:
        add("trend", "tr_none")
    un = cmp_res.get("unmatched") or {}
    ni, nr = len(un.get("inserted") or []), len(un.get("removed") or [])
    if ni or nr:
        add("scope", "sc", i=i(ni), r=i(nr))
    else:
        add("scope", "sc_none")

    # ---- C1 project finish
    pf = cmp_res.get("project_finish") or {}
    fp, fc = pf.get("previous") or {}, pf.get("current") or {}
    d = pf.get("delta_days")
    if fc.get("finish") and fp.get("finish") and d is not None:
        args = dict(a=fmt_date(fp["finish"], lang), b=fmt_date(fc["finish"], lang),
                    d=fnum(abs(d), 0 if float(abs(d)).is_integer() else 1, lang))
        add("c1", "fin_same" if abs(d) < 0.05 else ("fin_later" if d > 0 else "fin_earlier"), **args)
    drv = fc.get("driver")
    if drv:
        add("c1", "fin_driver", id=drv["id"], name=drv["name"], f=fmt_date(drv.get("finish"), lang))
        if drv.get("critical") is False:
            add("c1", "fin_driver_flag_no")
        if pf.get("driver_changed") is True and fp.get("driver"):
            add("c1", "fin_driver_changed", id=fp["driver"]["id"], name=fp["driver"]["name"])
        elif pf.get("driver_changed") is False:
            add("c1", "fin_driver_same")

    # ---- C2 critical path
    cp = cmp_res.get("critical_path")
    if cp:
        ne, nl = len(cp["entered"]), len(cp["left"])
        if ne or nl:
            add("c2", "cp", e=i(ne), l=i(nl), lc=i(cp["left_completed"]),
                n=i(cp["critical_current"]), p=i(cp["critical_previous"]))
        else:
            add("c2", "cp_none", n=i(cp["critical_current"]), p=i(cp["critical_previous"]))
        if cp.get("inserted_critical"):
            add("c2", "cp_inserted", n=i(cp["inserted_critical"]))
        if cp["float_fell_count"]:
            top = cp["float_fell_top"][0]
            add("c2", "cp_fell", n=i(cp["float_fell_count"]),
                d=fnum(top["float_fell_days"], 1, lang), id=top["id"])
        else:
            add("c2", "cp_fell_none")
        if cp["criterion_previous"] != cp["criterion_current"]:
            add("c2", "cp_basis_mixed")
        else:
            add("c2", "cp_basis_flag" if cp["criterion_current"] == "flag" else "cp_basis_float")

    # ---- C3 logic
    lg = cmp_res.get("logic")
    if lg:
        a, rm = len(lg["links_added"]), len(lg["links_removed"])
        l, t = len(lg["lag_changed"]), len(lg["type_changed"])
        if a or rm or l or t:
            add("c3", "lg", a=i(a), r=i(rm), l=i(l), t=i(t))
        else:
            add("c3", "lg_none")
        if lg.get("links_from_scope"):
            add("c3", "lg_scope", n=i(lg["links_from_scope"]))
        ca, cc, cr = (len(lg["constraints_added"]), len(lg["constraints_changed"]),
                      len(lg["constraints_removed"]))
        if ca or cc or cr:
            add("c3", "lg_con", a=i(ca), c=i(cc), r=i(cr))
            hard = sum(1 for x in lg["constraints_added"] + lg["constraints_changed"]
                       if x["type_after"] in HARD_CONSTRAINT_CODES)
            if hard:
                add("c3", "lg_hard", n=i(hard))
        else:
            add("c3", "lg_con_none")

    # ---- C4 durations
    du = cmp_res.get("duration_changed")
    if du is not None:
        if du:
            add("c4", "du", n=i(len(du)), up=i(sum(1 for x in du if x["delta_days"] > 0)),
                down=i(sum(1 for x in du if x["delta_days"] < 0)),
                net=fnum(sum(x["delta_days"] for x in du), 1, lang))
        else:
            add("c4", "du_none")

    # ---- C5 past rewritten
    pr = cmp_res.get("past_rewritten")
    if pr:
        if pr["activities"]:
            add("c5", "pr", n=i(pr["activities"]), s=i(len(pr["actual_start"])),
                f=i(len(pr["actual_finish"])), p=i(len(pr["percent_decreased"])))
            if pr["actual_removed"]:
                add("c5", "pr_removed", n=i(pr["actual_removed"]))
            if pr["time_of_day_only"]:
                add("c5", "pr_time", n=i(pr["time_of_day_only"]))
            add("c5", "pr_ask")
        else:
            add("c5", "pr_none")

    # ---- C6 quality
    q = cmp_res.get("quality")
    if q:
        rows = [m for m in q["metrics"] if m.get("change")]
        if rows:
            add("c6", "ql", t=i(len(rows)),
                w=i(sum(1 for m in rows if m["change"] == "worsened")),
                i=i(sum(1 for m in rows if m["change"] == "improved")),
                u=i(sum(1 for m in rows if m["change"] == "unchanged")))

        def names(crossing):
            return ", ".join(
                f"{m['code']} {metric_title(m['code'])}" if metric_title else m["code"]
                for m in q["metrics"] if m.get("crossed") == crossing)

        if names("pass->fail"):
            add("c6", "ql_bad", list=names("pass->fail"))
        if names("fail->pass"):
            add("c6", "ql_good", list=names("fail->pass"))
        ia, ib = q["indices"]["previous"].get("bei"), q["indices"]["current"].get("bei")
        if ia is not None and ib is not None:
            add("c6", "ql_bei", a=fnum(ia, 2, lang), b=fnum(ib, 2, lang))
    return out
