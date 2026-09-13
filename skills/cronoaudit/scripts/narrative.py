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
