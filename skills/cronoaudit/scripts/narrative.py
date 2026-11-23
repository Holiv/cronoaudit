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

import re
from decimal import ROUND_HALF_UP, Decimal

import i18n

R = {
    "en": {
        "net_hold": "The network holds: no out-of-sequence execution, so the forecast dates rest on logic the works follows.",
        "net_none": "There is no network to read: no activity is linked to another, so no forecast date is driven by logic. Zero out-of-sequence findings prove nothing here, because there is no sequence to break.",
        "net_open": "No out-of-sequence execution was found, but {u} of {o} {o?open activity has|open activities have} no predecessor or no successor ({s}%, against the {t}% the quality metric quotes). Those dates are not driven by logic; that the network holds can only be said of the part that is linked.",
        "planned_na": "Planned-to-date is unavailable: the baseline cost is not distributed in time in this file, so there is no \"ahead\" or \"behind\", no SV and no SPI to read. Weighted progress is {e}%.",
        "recon_none": "The file carries no earned value of its own (BCWP is zero on every activity: the tool did not compute it), so the reconciliation compares nothing. The earned figure here is the skill's alone.",
        "weight_top_np": "{g} carries {w}% of the budget and stands at {e}% earned; there is no planned figure to set it against.",
        "rain_none": "The calendars in use carry no non-working exceptions, so no period is reserved for bad weather and the exposure cannot be read from them. That is absence of data, not absence of risk.",
        "rain_few": "The calendars in use carry non-working exceptions, but no month reaches the reserve rule, so the weather exposure cannot be read from them. That is absence of data, not absence of risk.",
        "net_broken": "{n} {n?activity sits|activities sit} in violated logic ({a1} out of sequence, {a2} in total inversion). Every forecast date below is derived from a network the works does not follow; settle these before discussing a date.",
        "net_broken_crit": "The violated logic touches the critical path or the chain that drives the project finish: {pairs}.",
        "net_scoped": "{n} {n?pair|pairs} executed out of sequence: {pairs}. {n?It is|They are} off the critical path and off the chain that drives the project finish, so not every forecast date rests on {n?it|them}; up to {t} pairs in that position are named rather than read as a broken network (the threshold is ours).",
        "net_scoped_ms": "The driving {mm?chain|chains} of {ms} {mm?passes|pass} through {n?it|them}: settle {n?it|them} before quoting {mm?that milestone's date|those milestones' dates}.",
        "net_ms_item": "{name} (row {id})",
        "net_pair": "row {s}, {sn}, against its predecessor row {p}, {pn}",
        "progress": "Weighted progress is {e}% against {p}% planned: {d} {d?point|points} behind.",
        "progress_ahead": "Weighted progress is {e}% against {p}% planned: {d} {d?point|points} ahead.",
        "progress_even": "Weighted progress is {e}%, level with the {p}% planned.",
        "planned_from_file": "That planned figure is the file's own, the BCWS its scheduling tool computed: the file has no baseline cost spread in time, so the S-curve, SV, SPI and Earned Schedule are not available.",
        "recon_ok": "The skill's earned value matched the file's own on {m} of {c} {c?leaf|leaves} to the cent, zero against zero left out; the difference is explained.",
        "recon_all": "The skill's earned value matched the file's own on {c} of {c} {c?leaf|leaves} to the cent, zero against zero left out: nothing differs.",
        "recon_gap": "The skill's earned value differs from the file's on {u} {u?leaf|leaves} without explanation; check which baseline is in use and the earned-value method before trusting either figure.",
        "spi": "Cumulative SPI is {s}: the works has earned {pct}% of what the plan expected by now.",
        "method_gap": "The other earned-value method would read {alt}% instead of {e}%, a gap of {g} {g?point|points}. Switching method changes the curve, not the works.",
        "earned_before_plan": "{v} ({pct}% of the baseline cost) was earned before the first planned day, {d}: execution ahead of its baseline window, which the tool credits only when the status date reaches the window.",
        "weight_top": "{g} carries {w}% of the budget and stands at {e}% earned against {p}% planned.",
        "weight_behind": "{n} {n?group is|groups are} more than {d} {d?point|points} behind their own plan; the largest is {g}.",
        "weight_flat": "Everything sits in one group, so the weight distribution says nothing yet; group by a discovered field.",
        "prod_solid": "Of {n} {n?activity|activities} in progress with a trend, {s} rest on solid evidence: {ahead} ahead, {rep} to reprogram, {abs} with the baseline missed and the float absorbing it, {crit} that would enter the critical path.",
        "prod_thin": "{t} {t?projection rests|projections rest} on thin evidence or a percent-derived quantity; read them as questions, not verdicts.",
        "prod_inconsistent": "{k} {k?activity has|activities have} an inconsistent measurement and no pace verdict: the executed quantity and the physical percent disagree. Row {id}, {name}: {q}% by quantity, {p}% physical.",
        "method_gap_from": "{s}% of that gap comes from row {id}, {name}: {pc}% complete by duration, {pp}% physical.",
        "method_gap_rows": "{k} {k?activity differs|activities differ} by 20 points or more between the two percentages; they are listed under the curve.",
        "rate_falling": "{r} is slowing: planned {p} a day, {g} practised to date, {rc} in the last thirty days.",
        "q_fail": "The network fails {n} of the quantitative metrics: {list}.",
        "q_pass_all": "The network passes every quantitative metric with a threshold.",
        "bei": "Of {d} {d?activity|activities} due by the status date, {a} finished on time: a baseline execution index of {b}.",
        "float_deadline": "{f}% of incomplete activities carry more than 44 working days of float while {m} of {mm} {mm?milestone|milestones} have no deadline: the float is not slack, it is an unconstrained plan.",
        "float_no_milestones": "{f}% of incomplete activities carry more than 44 working days of float, and the file has no milestone a deadline could constrain: nothing ties the finish to a date, so read the float as a question, not as slack.",
        "float_deadline_set": "{f}% of incomplete activities carry more than 44 working days of float, although {mm} of {mm} {mm?milestone carries|milestones carry} a deadline: the float does not come from an unconstrained finish. It may be real slack or a missing link; read it as a question.",
        "es_behind": "Earned Schedule falls on {es}: the plan reached today's earned value {d} {d?day|days} ago, a schedule efficiency SPI(t) of {spi}.",
        "es_ahead": "Earned Schedule falls on {es}, {d} {d?day|days} ahead of today: SPI(t) {spi}.",
        "es_level": "Earned Schedule falls on the status date, {es}: the works has earned what the plan expected by today, SPI(t) {spi}.",
        "es_ieac": "At this efficiency the independent finish is {ieac}, {gap} {gap?day|days} after the schedule's own finish, {sched}. Either the logic is optimistic or the remainder will run at a pace not yet seen.",
        "es_ieac_early": "At this efficiency the independent finish is {ieac}, {gap} {gap?day|days} before the schedule's own finish, {sched}. The schedule allows the remainder more time than the pace achieved so far would need: either it carries margin or it assumes a slower pace from here on.",
        "es_ieac_agree": "At this efficiency the independent finish is {ieac} and the schedule's own finish is {sched}: within {tol} days of each other, the achieved pace and the schedule agree on the date.",
        "es_tspi_easy": "TSPI is {t}: the remainder can finish on the planned date at the plan's own pace.",
        "es_tspi_hard": "TSPI is {t}: the remainder must run {pct}% above the plan to finish on the planned date.",
        "es_tspi_hard_early": "TSPI is {t}: the remainder must run {pct}% above the plan to finish on the planned date. Modest because most of the duration is still ahead, not because the lag is small.",
        "es_tspi_no": "TSPI is {t}: the remainder would need {pct}% above the plan, which the literature treats as unrecoverable in practice.",
        "es_tspi_plain": "TSPI is {t}: the pace the remainder needs, relative to the plan's, to finish on the planned date.",
        "la_no": "The next {w} {w?week|weeks} plan {p}% of earning; the practised rate delivers {q}%. Not reachable without a change of pace.",
        "dl_none": "No future milestone has a deadline ({m} {m?milestone|milestones}): there is nothing in the file to measure the schedule against. Enter the contract dates as Deadline on the milestones.",
        "dl_past": "{n} of the {m} milestones with a deadline already finish after it in the current schedule; the worst is row {id}, {name}, {d} {d?day|days} past it.",
        "dl_ok_now": "All {m} milestones with a deadline finish within it in the current schedule. The smallest margin is row {id}, {name}: {d} {d?day|days}.",
        "dl_p80": "With the slippage that 80% of the activities have not exceeded ({p} {p?day|days}), {k} more {k?milestone passes|milestones pass} the deadline: {k?row|rows} {ids}.",
        "dl_origin": "The delay of row {id} starts at row {oid}, {oname} (+{od} {od?day|days} against the baseline).",
        "dl_some_missing": "{k} future {k?milestone has|milestones have} no deadline and {k?is|are} not measured here.",
        "dl_past_one": "The only milestone with a deadline already finishes after it in the current schedule: row {id}, {name}, {d} {d?day|days} past it.",
        "dl_ok_now_one": "The only milestone with a deadline finishes within it in the current schedule: row {id}, {name}, with {d} {d?day|days} of margin.",
        "la_yes": "The next {w} {w?week|weeks} plan {p}% of earning and the practised rate delivers {q}%: reachable.",
        "rg_out": "{n} {n?group|groups} cannot reach their baseline finish at the practised pace; {g} needs {r}× its current rate.",
        "rg_ok": "Every group with a trend is on pace or within a stretch of its baseline finish.",
        "rain": "{s}% of the remaining cost sits in months the calendars reserve for bad weather, {t}% if everything slips thirty days.",
        "fx_origins": "{o} of {m} {m?future milestone|future milestones} trace to a named origin; activity {id}, {name}, originates delay on {k} of them.",
        "fx_origins_unnamed": "{o} of {m} {m?future milestone|future milestones} trace to a named origin; no single activity originates delay on more than one.",
        "fx_none": "No future milestone carries variance above the threshold, so no origin is named.",
        "fx_bl_moved": "On the driving chain of {m}, row {id}, {name}, shows a variance of {v} working {v?day|days} against a baseline that moved {sb}{b} calendar {b?day|days} this cycle: part of that variance is the reference moving, not the works.",
        "fx_cal": "Calendar forensics flags {n} {n?calendar|calendars}: {list}.",
        "fx_oos_rising": "Out-of-sequence execution is rising, from {a} {a?pair|pairs} a month to {b}: the practice is accelerating.",
        "fx_oos_falling": "Out-of-sequence execution is falling, from {a} {a?pair|pairs} a month to {b}.",
        "fx_slip": "Of {n} {n?started activity|started activities}, {early} started early and {late} late; the median start was {p50} {p50?day|days} {dir} the baseline.",
        "fx_slip_on": "Of {n} {n?started activity|started activities}, {early} started early and {late} late; the median start fell on the baseline date.",
        "early": "before", "late": "after",
        "syn_label": "Executive synthesis",
        "syn_written": "Written by {who} from the figures in this report, on {when}.",
    },
    "pt": {
        "net_hold": "A rede se sustenta: não há execução fora de sequência, então as datas de tendência se apoiam em lógica que a obra segue.",
        "net_none": "Não há rede para ler: nenhuma atividade está ligada a outra, então nenhuma data de tendência é conduzida por lógica. Zero achados de execução fora de sequência não provam nada aqui, porque não há sequência para quebrar.",
        "net_open": "Não foi encontrada execução fora de sequência, mas {u} de {o} {o?atividade em aberto não tem|atividades em aberto não têm} predecessora ou não {o?tem|têm} sucessora ({s}%, contra os {t}% que a métrica de qualidade cita). Essas datas não são conduzidas por lógica; que a rede se sustenta só pode ser dito da parte que está ligada.",
        "planned_na": "O previsto até a data está indisponível: o custo de linha de base não está distribuído no tempo neste arquivo, então não há \"à frente\" ou \"atrás\", nem VP, nem IDP para ler. O avanço ponderado é {e}%.",
        "recon_none": "O arquivo não traz valor agregado próprio (o BCWP é zero em todas as atividades: a ferramenta não calculou), então a conciliação não compara nada. O valor agregado aqui é só o da skill.",
        "weight_top_np": "{g} carrega {w}% do orçamento e está em {e}% realizado; não há previsto com que comparar.",
        "rain_none": "Os calendários em uso não têm nenhuma exceção de dia não útil, então nenhum período está reservado para tempo ruim e a exposição não pode ser lida deles. É ausência de dado, não ausência de risco.",
        "rain_few": "Os calendários em uso têm exceções de dia não útil, mas nenhum mês alcança a regra de reserva, então a exposição ao tempo ruim não pode ser lida deles. É ausência de dado, não ausência de risco.",
        "net_broken": "{n} {n?atividade está|atividades estão} em lógica violada ({a1} fora de sequência, {a2} em inversão total). Toda data de tendência abaixo deriva de uma rede que a obra não segue; resolva isso antes de discutir uma data.",
        "net_broken_crit": "A lógica violada toca o caminho crítico ou a cadeia que conduz o término do projeto: {pairs}.",
        "net_scoped": "{n} {n?par executado|pares executados} fora de sequência: {pairs}. {n?Ele não está|Eles não estão} no caminho crítico nem na cadeia que conduz o término do projeto, então nem toda data de tendência se apoia {n?nele|neles}; até {t} pares nessa posição são nomeados em vez de lidos como rede quebrada (o limite é nosso).",
        "net_scoped_ms": "{mm?A cadeia condutora|As cadeias condutoras} de {ms} {mm?passa|passam} por {n?esse par|esses pares}: resolva antes de citar {mm?a data desse marco|as datas desses marcos}.",
        "net_ms_item": "{name} (linha {id})",
        "net_pair": "linha {s}, {sn}, contra a predecessora linha {p}, {pn}",
        "progress": "O avanço ponderado é {e}% contra {p}% previsto: {d} {d?ponto|pontos} atrás.",
        "progress_ahead": "O avanço ponderado é {e}% contra {p}% previsto: {d} {d?ponto|pontos} à frente.",
        "progress_even": "O avanço ponderado é {e}%, igual aos {p}% previstos.",
        "planned_from_file": "Esse previsto é o do próprio arquivo, o BCWS que a ferramenta de cronograma calculou: o arquivo não traz o custo de linha de base distribuído no tempo, então curva S, VP, IDP e Earned Schedule não estão disponíveis.",
        "recon_ok": "O valor agregado da skill bateu com o do arquivo em {m} de {c} {c?folha|folhas} ao centavo, zero contra zero fica fora; a diferença está explicada.",
        "recon_all": "O valor agregado da skill bateu com o do arquivo em {c} de {c} {c?folha|folhas} ao centavo, zero contra zero fica fora: nada difere.",
        "recon_gap": "O valor agregado da skill difere do arquivo em {u} {u?folha|folhas} sem explicação; confira qual linha de base está em uso e o método antes de confiar em qualquer dos dois.",
        "spi": "O IDP acumulado é {s}: a obra agregou {pct}% do que o plano esperava até agora.",
        "method_gap": "O outro método de valor agregado leria {alt}% em vez de {e}%, diferença de {g} {g?ponto|pontos}. Trocar o método muda a curva, não a obra.",
        "earned_before_plan": "{v} ({pct}% do custo de linha de base) foi agregado antes do primeiro dia previsto, {d}: execução antes da janela de linha de base, que a ferramenta só credita quando a data de status alcança a janela.",
        "weight_top": "{g} carrega {w}% do orçamento e está em {e}% realizado contra {p}% previsto.",
        "weight_behind": "{n} {n?grupo está|grupos estão} mais de {d} {d?ponto|pontos} atrás do próprio previsto; o maior é {g}.",
        "weight_flat": "Tudo está num único grupo, então a distribuição de peso ainda não diz nada; agrupe por um campo descoberto.",
        "prod_solid": "Das {n} {n?atividade em andamento|atividades em andamento} com tendência, {s} se apoiam em evidência sólida: {ahead} adiantadas, {rep} para reprogramar, {abs} com a linha de base perdida e a folga absorvendo, {crit} que entrariam no caminho crítico.",
        "prod_thin": "{t} {t?projeção se apoia|projeções se apoiam} em evidência fina ou em quantidade derivada de percentual; leia como pergunta, não como veredicto.",
        "prod_inconsistent": "{k} {k?atividade tem|atividades têm} medição inconsistente e nenhum veredicto de ritmo: a quantidade executada e o % físico não batem. Linha {id}, {name}: {q}% pela quantidade, {p}% físico.",
        "method_gap_from": "{s}% dessa diferença vem da linha {id}, {name}: {pc}% concluída pela duração, {pp}% físico.",
        "method_gap_rows": "{k} {k?atividade difere|atividades diferem} em 20 pontos ou mais entre os dois percentuais; estão listadas abaixo da curva.",
        "rate_falling": "{r} está desacelerando: previsto {p} por dia, {g} praticado até a data, {rc} nos últimos trinta dias.",
        "q_fail": "A rede não atende {n} das métricas quantitativas: {list}.",
        "q_pass_all": "A rede atende todas as métricas quantitativas com limiar.",
        "bei": "De {d} {d?atividade devida|atividades devidas} até a data de status, {a} {a?terminou|terminaram} no prazo: índice de execução da linha de base de {b}.",
        "float_deadline": "{f}% das atividades incompletas carregam mais de 44 dias úteis de folga enquanto {m} de {mm} {mm?marco|marcos} não têm data limite: a folga não é margem, é plano sem restrição.",
        "float_no_milestones": "{f}% das atividades incompletas carregam mais de 44 dias úteis de folga, e o arquivo não tem marco que uma data limite pudesse restringir: nada prende o término a uma data, então leia a folga como pergunta, não como margem.",
        "float_deadline_set": "{f}% das atividades incompletas carregam mais de 44 dias úteis de folga, embora {mm} de {mm} {mm?marco tenha|marcos tenham} data limite: a folga não vem de término sem restrição. Pode ser margem real ou vínculo faltando; leia como pergunta.",
        "es_behind": "O Earned Schedule cai em {es}: o plano alcançou o realizado de hoje há {d} {d?dia|dias}, eficiência de prazo SPI(t) de {spi}.",
        "es_ahead": "O Earned Schedule cai em {es}, {d} {d?dia|dias} à frente de hoje: SPI(t) {spi}.",
        "es_level": "O Earned Schedule cai na própria data de status, {es}: a obra agregou o que o plano esperava até hoje, SPI(t) {spi}.",
        "es_ieac": "Nesta eficiência o término independente é {ieac}, {gap} {gap?dia|dias} depois do término do próprio cronograma, {sched}. Ou a lógica está otimista, ou o restante vai rodar num ritmo que ainda não aconteceu.",
        "es_ieac_early": "Nesta eficiência o término independente é {ieac}, {gap} {gap?dia|dias} antes do término do próprio cronograma, {sched}. O cronograma dá ao restante mais tempo do que o ritmo realizado até aqui precisaria: ou carrega margem, ou supõe um ritmo mais lento daqui em diante.",
        "es_ieac_agree": "Nesta eficiência o término independente é {ieac} e o término do próprio cronograma é {sched}: com até {tol} dias de diferença, o ritmo realizado e o cronograma concordam na data.",
        "es_tspi_easy": "O TSPI é {t}: o restante termina na data prevista no ritmo do próprio plano.",
        "es_tspi_hard": "O TSPI é {t}: o restante precisa rodar {pct}% acima do plano para terminar na data prevista.",
        "es_tspi_hard_early": "O TSPI é {t}: o restante precisa rodar {pct}% acima do plano para terminar na data prevista. Modesto porque a maior parte da duração ainda está pela frente, não porque o atraso seja pequeno.",
        "es_tspi_no": "O TSPI é {t}: o restante precisaria de {pct}% acima do plano, o que a literatura trata como irrecuperável na prática.",
        "es_tspi_plain": "O TSPI é {t}: o ritmo de que o restante precisa, relativo ao do plano, para terminar na data prevista.",
        "la_no": "As próximas {w} {w?semana|semanas} preveem {p}% de medição; o ritmo praticado entrega {q}%. Não alcançável sem mudança de ritmo.",
        "dl_none": "Nenhum marco futuro tem data limite ({m} {m?marco|marcos}): o arquivo não tem contra o que medir o prazo. Cadastre as datas contratuais como Data Limite nos marcos.",
        "dl_past": "{n} dos {m} marcos com data limite já terminam depois dela no cronograma atual; o pior é a linha {id}, {name}, {d} {d?dia|dias} além.",
        "dl_ok_now": "Os {m} marcos com data limite terminam dentro dela no cronograma atual. A menor margem é a da linha {id}, {name}: {d} {d?dia|dias}.",
        "dl_p80": "Com o escorregamento que 80% das atividades não ultrapassaram ({p} {p?dia|dias}), mais {k} {k?marco passa|marcos passam} da data limite: {k?linha|linhas} {ids}.",
        "dl_origin": "O atraso da linha {id} nasce na linha {oid}, {oname} (+{od} {od?dia|dias} contra a linha de base).",
        "dl_some_missing": "{k} {k?marco futuro não tem|marcos futuros não têm} data limite e não {k?é medido|são medidos} aqui.",
        "dl_past_one": "O único marco com data limite já termina depois dela no cronograma atual: linha {id}, {name}, {d} {d?dia|dias} além.",
        "dl_ok_now_one": "O único marco com data limite termina dentro dela no cronograma atual: linha {id}, {name}, com {d} {d?dia|dias} de margem.",
        "la_yes": "As próximas {w} {w?semana|semanas} preveem {p}% de medição e o ritmo praticado entrega {q}%: alcançável.",
        "rg_out": "{n} {n?grupo não alcança|grupos não alcançam} o término de linha de base no ritmo praticado; {g} precisa de {r}× o ritmo atual.",
        "rg_ok": "Todo grupo com tendência está no ritmo ou a um esforço do término de linha de base.",
        "rain": "{s}% do custo remanescente cai em meses que os calendários reservam para tempo ruim, {t}% se tudo escorregar trinta dias.",
        "fx_origins": "{o} de {m} {m?marco futuro|marcos futuros} têm origem nomeada; a atividade {id}, {name}, origina atraso em {k} deles.",
        "fx_origins_unnamed": "{o} de {m} {m?marco futuro|marcos futuros} têm origem nomeada; nenhuma atividade isolada origina atraso em mais de um.",
        "fx_none": "Nenhum marco futuro carrega variação acima do limiar, então nenhuma origem é nomeada.",
        "fx_bl_moved": "Na cadeia condutora de {m}, a linha {id}, {name}, mostra variação de {v} {v?dia útil|dias úteis} contra uma linha de base que se moveu {sb}{b} {b?dia corrido|dias corridos} neste ciclo: parte dessa variação é a referência se movendo, não a obra.",
        "fx_cal": "A forense de calendário sinaliza {n} {n?calendário|calendários}: {list}.",
        "fx_oos_rising": "A execução fora de sequência está subindo, de {a} {a?par|pares} por mês para {b}: a prática está acelerando.",
        "fx_oos_falling": "A execução fora de sequência está caindo, de {a} {a?par|pares} por mês para {b}.",
        "fx_slip": "De {n} {n?atividade iniciada|atividades iniciadas}, {early} {early?começou|começaram} cedo e {late} tarde; o início mediano foi {p50} {p50?dia|dias} {dir} da linha de base.",
        "fx_slip_on": "De {n} {n?atividade iniciada|atividades iniciadas}, {early} {early?começou|começaram} cedo e {late} tarde; o início mediano caiu na data da linha de base.",
        "early": "antes", "late": "depois",
        "syn_label": "Síntese executiva",
        "syn_written": "Redigida por {who} a partir dos números deste relatório, em {when}.",
    },
}


def _n(v, d=1):
    if v is None:
        return "—"
    return f"{v:,.{d}f}" if isinstance(v, float) else f"{v:,}"


_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})(?:T\d{2}:\d{2}(?::\d{2})?)?\b")


def _dates(text: str, lang: str) -> str:
    """Dates inside a sentence, in the report's language. The sidecar of readings
    is quoted as it is, so a raw timestamp must not survive into it."""
    if lang == "pt":
        return _ISO_DATE.sub(lambda m: f"{m.group(3)}/{m.group(2)}/{m.group(1)}", text)
    return _ISO_DATE.sub(lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}", text)


def gate_sentences(gate: dict, lang: str) -> list:
    """The scoped network warning: the pairs by name and the milestones whose
    driving chain passes through them. Shared by the verdict reading and the
    banner over the findings."""
    T = R.get(lang, R["en"])
    pairs = gate.get("pairs") or []
    if not pairs:
        return []
    n = gate.get("pair_count") or len(pairs)
    names = "; ".join(i18n.fmt(T["net_pair"], s=p["succ_id"], sn=p["succ_name"],
                               p=p["pred_id"], pn=p["pred_name"]) for p in pairs)
    out = [i18n.fmt(T["net_scoped"], n=fnum(n, 0, lang), pairs=names,
                    t=fnum(gate.get("threshold_pairs"), 0, lang))]
    ms = gate.get("milestones") or []
    if ms:
        sep = " e " if lang == "pt" else " and "
        lst = [i18n.fmt(T["net_ms_item"], id=m["id"], name=m["name"]) for m in ms]
        joined = lst[0] if len(lst) == 1 else ", ".join(lst[:-1]) + sep + lst[-1]
        out.append(i18n.fmt(T["net_scoped_ms"], ms=joined, n=fnum(n, 0, lang),
                            mm=fnum(len(ms), 0, lang)))
    return out


def build(payload: dict, lang: str) -> dict:
    T = R.get(lang, R["en"])
    m = payload.get("meta") or {}
    out: dict[str, list] = {}

    def add(section, key, **kw):
        try:
            out.setdefault(section, []).append(_dates(i18n.fmt(T[key], **kw), lang))
        except (KeyError, ValueError, TypeError):
            pass

    def _n(v, d=1):
        # Numbers the way the report's language writes them: "35,56" in Portuguese.
        # A whole number stays whole whatever precision was asked for.
        if v is None:
            return "—"
        return fnum(v, d if isinstance(v, float) else 0, lang)

    # ---- verdict
    f = {x["code"]: x for x in payload.get("findings", [])}
    net = (f.get("A1", {}).get("count") or 0) + (f.get("A2", {}).get("count") or 0)
    # A reading is stated only when the input it needs exists. `inputs` says what
    # the file has; where something is missing the sentence says THAT, instead of
    # reading a zero that is only the absence of data.
    inputs = m.get("inputs") or {}
    netw = inputs.get("network") or {}
    gate = inputs.get("network_gate") or {}
    if net and gate.get("scope") == "scoped":
        # One or few pairs on a side branch are named, not read as a broken network.
        for sentence in gate_sentences(gate, lang):
            out.setdefault("verdict", []).append(_dates(sentence, lang))
    elif net:
        add("verdict", "net_broken", n=_n(net, 0), a1=_n(f["A1"]["count"], 0), a2=_n(f["A2"]["count"], 0))
        if gate.get("pairs") and set(gate.get("reasons") or []) & {"critical", "finish_chain"} \
                and "count" not in (gate.get("reasons") or []):
            add("verdict", "net_broken_crit", pairs="; ".join(
                i18n.fmt(T["net_pair"], s=p["succ_id"], sn=p["succ_name"], p=p["pred_id"],
                         pn=p["pred_name"]) for p in gate["pairs"]))
    elif netw.get("state") == "none":
        add("verdict", "net_none")
    elif netw.get("state") == "open":
        add("verdict", "net_open", u=_n(netw["unlinked"], 0), o=_n(netw["open"], 0),
            s=_n(netw["share_pct"], 1), t=_n(netw["threshold_pct"], 0))
    elif netw.get("state") == "linked":
        # Only a network known to be linked "holds"; no state is no reading.
        add("verdict", "net_hold")
    e, p = m.get("percent_earned"), m.get("percent_planned_file")
    planned_ok = inputs.get("planned_available", True)
    if e is not None and not planned_ok:
        add("verdict", "planned_na", e=_n(e, 2))
    elif e is not None and p is not None:
        # Level is its own reading: "0.00 points behind" is a direction the data lacks.
        key = "progress_even" if abs(e - p) < 0.005 else ("progress_ahead" if e > p else "progress")
        add("verdict", key, e=_n(e, 2), p=_n(p, 2), d=_n(abs(e - p), 2))
        # The planned figure can come from the file's own BCWS while the S-curve has
        # nothing to spread in time (a schedule saved by the tool, without a time-phased
        # baseline): two readings, two sources. Say which one this is.
        if ((payload.get("scurve") or {}).get("inputs") or {}).get("planned_available") is False:
            add("verdict", "planned_from_file")
    rc = m.get("reconciliation") or {}
    if rc.get("file_computed_ev") is False:
        add("verdict", "recon_none")
    elif rc.get("leaves_compared"):
        if rc.get("unexplained"):
            add("verdict", "recon_gap", u=_n(rc["unexplained"], 0))
        elif rc.get("matches_to_cent") == rc["leaves_compared"]:
            # Nothing differs, so there is no difference to call explained.
            add("verdict", "recon_all", c=_n(rc["leaves_compared"], 0))
        else:
            add("verdict", "recon_ok", m=_n(rc["matches_to_cent"], 0), c=_n(rc["leaves_compared"], 0))

    # ---- S-curve
    s = payload.get("scurve") or {}
    T_ = s.get("totals") or {}
    if T_.get("spi") is not None:
        # The percentage is read from the index as displayed, so "0,902" and "90,2%"
        # cannot disagree in the same sentence.
        add("scurve", "spi", s=_n(T_["spi"], 3), pct=_n(half_up(T_["spi"], 3) * 100, 1))
    if T_.get("earned_alt_pct") is not None and abs(T_.get("method_gap_points") or 0) >= 0.01:
        add("scurve", "method_gap", alt=_n(T_["earned_alt_pct"], 2), e=_n(T_.get("earned_pct"), 2),
            g=_n(abs(T_["method_gap_points"]), 2))
        top = ((s.get("percent_vs_physical") or {}).get("rows") or [None])[0]
        if top and (top.get("share_of_gap_pct") or 0) >= 50:
            add("scurve", "method_gap_from", id=top["id"], name=top["name"],
                s=_n(min(100.0, top["share_of_gap_pct"]), 0),
                pc=_n(top["percent_complete"], 0), pp=_n(top["physical_percent"], 0))
        elif (s.get("percent_vs_physical") or {}).get("count"):
            add("scurve", "method_gap_rows", k=_n(s["percent_vs_physical"]["count"], 0))
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
        if planned_ok and top.get("planned_pct") is not None:
            add("groups", "weight_top", g=top["label"], w=_n(top["weight_pct"], 1),
                e=_n(top["earned_pct"], 1), p=_n(top["planned_pct"], 1))
        else:
            add("groups", "weight_top_np", g=top["label"], w=_n(top["weight_pct"], 1),
                e=_n(top["earned_pct"], 1))
        behind = [r for r in g if planned_ok
                  and (r["planned_pct"] or 0) - (r["earned_pct"] or 0) > 5]
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
        bad = [a for a in acts if a.get("measurement_inconsistent")]
        if bad:
            b0 = bad[0]
            add("productivity", "prod_inconsistent", k=_n(len(bad), 0), id=b0["id"], name=b0["name"],
                q=_n(b0.get("qty_pct"), 0), p=_n(b0.get("physical_percent"), 0))
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
            add("quality", "q_fail", n=_n(len(fails), 0), list=", ".join(
                " ".join(filter(None, (x.get("code"), x.get("title")))) for x in fails))
        else:
            add("quality", "q_pass_all")
    I = q.get("indices") or {}
    if I.get("bei") is not None:
        add("quality", "bei", d=_n(I["bei_due"], 0), a=_n(I["bei_on_time"], 0), b=_n(I["bei"], 2))
    q6 = next((x for x in q.get("metrics", []) if x["code"] == "Q6"), None)
    QL = q.get("qualitative") or {}
    # High float is read only when Q6 fails, and "unconstrained plan" only when
    # some milestone has no deadline: with every milestone constrained the float
    # has another cause, and the reading asks instead of concluding.
    if q6 and q6.get("share_pct") and q6.get("status") == "fail" and QL.get("milestones") == 0:
        add("quality", "float_no_milestones", f=_n(q6["share_pct"], 0))
    elif q6 and q6.get("share_pct") and q6.get("status") == "fail" and QL.get("milestones"):
        no_dl = QL.get("milestones_without_deadline")
        if no_dl:
            add("quality", "float_deadline", f=_n(q6["share_pct"], 0), m=_n(no_dl, 0), mm=_n(QL["milestones"], 0))
        elif no_dl == 0:
            add("quality", "float_deadline_set", f=_n(q6["share_pct"], 0), mm=_n(QL["milestones"], 0))

    # ---- forecast
    fc = payload.get("forecast") or {}
    E = fc.get("earned_schedule") or {}
    if E.get("available"):
        if abs(E["sv_t_days"]) < 0.5:
            add("forecast", "es_level", es=E["es_date"], spi=_n(E["spi_t"], 3))
        elif E["sv_t_days"] < 0:
            add("forecast", "es_behind", es=E["es_date"], d=_n(abs(E["sv_t_days"]), 0), spi=_n(E["spi_t"], 3))
        else:
            add("forecast", "es_ahead", es=E["es_date"], d=_n(E["sv_t_days"], 0), spi=_n(E["spi_t"], 3))
        # gap = IEAC(t) - schedule finish, classified by forecast.gap_reading. Only
        # the "later" side supports "the logic is optimistic"; the earlier side says
        # the schedule allows more time than the pace needs; close is agreement.
        key = {"later": "es_ieac", "earlier": "es_ieac_early", "agree": "es_ieac_agree"}.get(E.get("gap_reading"))
        if E.get("ieac_t_date") and key and E.get("gap_vs_schedule_days") is not None:
            add("forecast", key, ieac=E["ieac_t_date"], gap=_n(abs(E["gap_vs_schedule_days"]), 0),
                sched=E.get("schedule_finish"), tol=_n(E.get("gap_agree_days"), 0))
        if E.get("tspi") is not None:
            # An unknown verdict states the figure only, never the hard sentence.
            key = {"recoverable": "es_tspi_easy", "hard": "es_tspi_hard", "unrecoverable": "es_tspi_no"}.get(E.get("tspi_verdict"), "es_tspi_plain")
            # "Modest because most of the duration is ahead" is said only when it is.
            at, pd = E.get("at_days"), E.get("pd_days")
            if key == "es_tspi_hard" and at is not None and pd and at / pd < 0.5:
                key = "es_tspi_hard_early"
            add("forecast", key, t=_n(E["tspi"], 3), pct=_n(max(0.0, (E["tspi"] - 1) * 100), 1))
    for w in fc.get("lookahead") or []:
        if w.get("reachable") is not None:
            add("forecast", "la_yes" if w["reachable"] else "la_no", w=w["weeks"], p=_n(w["planned_earning_pct"], 2), q=_n(w["projected_pct"], 2))
            break
    rg = [r for r in fc.get("rates_by_group") or [] if r.get("verdict") == "out of reach"]
    # "Every group with a trend is on pace" needs at least one group with a trend.
    if any(r.get("verdict") for r in fc.get("rates_by_group") or []):
        if rg:
            worst = max(rg, key=lambda r: r.get("ratio_required_over_practised") or 0)
            add("forecast", "rg_out", n=_n(len(rg), 0), g=worst["group"], r=_n(worst["ratio_required_over_practised"], 1))
        else:
            add("forecast", "rg_ok")
    RX = fc.get("rain_exposure") or {}
    if RX.get("available") and RX.get("readable") is False:
        add("forecast", "rain_none" if RX.get("unreadable_reason") == "no_exceptions" else "rain_few")
    elif RX.get("share_in_reserve_pct") is not None:
        add("forecast", "rain", s=_n(RX["share_in_reserve_pct"], 0), t=_n(RX.get("share_if_slips_30_days_pct"), 0))

    # ---- deadlines: each future milestone against its deadline
    DL = payload.get("deadlines") or {}
    if DL.get("rows"):
        rows_by = {r["id"]: r for r in DL["rows"]}
        if not DL.get("with_deadline"):
            add("deadlines", "dl_none", m=_n(len(DL["rows"]), 0))
        else:
            tight = DL["tightest"]
            if DL["past_now"]:
                worst = min((rows_by[i] for i in DL["past_now"]), key=lambda r: r["margin_days"])
                add("deadlines", "dl_past_one" if DL["with_deadline"] == 1 else "dl_past",
                    n=_n(len(DL["past_now"]), 0), m=_n(DL["with_deadline"], 0),
                    id=worst["id"], name=worst["name"], d=_n(-worst["margin_days"], 0))
            else:
                add("deadlines", "dl_ok_now_one" if DL["with_deadline"] == 1 else "dl_ok_now",
                    m=_n(DL["with_deadline"], 0), id=tight["id"],
                    name=tight["name"], d=_n(tight["margin_days"], 0))
            extra = [i for i in DL["past_p80"] if i not in DL["past_now"]]
            if extra and DL.get("p80_days"):
                add("deadlines", "dl_p80", p=_n(DL["p80_days"], 0), k=_n(len(extra), 0),
                    ids=", ".join(str(i) for i in extra))
            focus = worst if DL["past_now"] else tight
            if focus.get("origin_id") and focus["origin_id"] != focus["id"]:
                add("deadlines", "dl_origin", id=focus["id"], oid=focus["origin_id"],
                    oname=focus.get("origin_name") or "—", od=_n(focus.get("origin_days"), 0))
            if DL.get("without_deadline"):
                add("deadlines", "dl_some_missing", k=_n(DL["without_deadline"], 0))

    # ---- forensics
    fx = payload.get("forensics") or {}
    FS = fx.get("summary") or {}
    if FS.get("milestones"):
        if FS.get("with_origin") and FS.get("origins"):
            o = FS["origins"][0]
            add("forensics", "fx_origins", o=_n(FS["with_origin"], 0), m=_n(FS["milestones"], 0), id=o["id"],
                name=o.get("name") or "—", k=_n(o["milestones"], 0))
        elif FS.get("with_origin"):
            # Origins exist but none is listed: never "no milestone carries variance".
            add("forensics", "fx_origins_unnamed", o=_n(FS["with_origin"], 0), m=_n(FS["milestones"], 0))
        else:
            add("forensics", "fx_none")
    seen_bl = set()
    for ms in fx.get("milestones") or []:
        for node in ms.get("chain") or []:
            if node.get("baseline_moved_days") and node["id"] not in seen_bl:
                seen_bl.add(node["id"])
                bm = node["baseline_moved_days"]
                add("forensics", "fx_bl_moved", m=ms["name"], id=node["id"], name=node["name"],
                    v=_n(node.get("variance_days"), 0), b=_n(abs(bm), 0),
                    sb="+" if bm > 0 else "−")
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
        if round(abs(p50)) == 0:
            add("forensics", "fx_slip_on", n=_n(SL["sample"], 0), early=_n(SL["started_early"], 0),
                late=_n(SL["started_late"], 0))
        else:
            add("forensics", "fx_slip", n=_n(SL["sample"], 0), early=_n(SL["started_early"], 0),
                late=_n(SL["started_late"], 0), p50=_n(abs(p50), 0), dir=T["early"] if p50 < 0 else T["late"])
    return out


# ---------------------------------------------------------------------------
# The cycle comparison. Same contract as above: every sentence is built from the
# comparison's own figures, and a figure that is missing produces no sentence.
# ---------------------------------------------------------------------------
RC = {
    "en": {
        "mv": "Weighted progress went from {a}% to {b}%: {m} {m?point|points}. Per-activity progress explains {x} of them and {r} {r?is|are} not explained by work done.",
        "mv_over": "Weighted progress went from {a}% to {b}%: {m} {m?point|points}. Per-activity progress adds up to {x}, more than the movement: {r} {r?point was|points were} taken off by something other than work done.",
        "mv_terms": "The difference is named: {list}.",
        "mv_terms_rest": "The difference is named in part: {list}; {r} {r?point remains|points remain} unexplained.",
        "term_rem_1": "{p} {p?point|points} from the earned value erased with a removed activity (row {id} of the previous delivery, {name}, at {pct}%: {v})",
        "term_rem_n": "{p} {p?point|points} from the earned value erased with {n} removed activities ({v}; the largest is row {id} of the previous delivery, {name}, at {pct}%)",
        "term_ins": "{p} {p?point|points} from the earned value of {n} inserted {n?activity|activities}",
        "term_chg": "{p} {p?point|points} from baseline cost changed on {n} {n?activity|activities} present in both deliveries",
        "term_bac": "{p} {p?point|points} from the budget at completion, which went from {a} to {b} ({parts})",
        "bac_ins": "+{v} inserted", "bac_rem": "−{v} removed", "bac_chg": "{v} in changed baselines",
        "mv_clean": "Weighted progress went from {a}% to {b}%: {m} {m?point|points}, all of it explained by per-activity progress.",
        "tr": "{e} {e?activity|activities} moved their dates with actual dates behind them and {r} with none; the baseline itself moved on {b}.",
        "tr_none": "No activity moved its dates between the two deliveries.",
        "sc": "{i} {i?activity|activities} inserted and {r} removed.",
        "sc_none": "No activity was inserted or removed: the scope is the same in both deliveries.",
        "fin_later": "The project finish moved from {a} to {b}: {d} {d?calendar day|calendar days} later.",
        "fin_earlier": "The project finish moved from {a} to {b}: {d} {d?calendar day|calendar days} earlier.",
        "fin_same": "The project finish did not move: {b} in both deliveries.",
        "fin_driver": "What holds the current date is row {id}, {name}, finishing on {f}. This is an approximation: the last-finishing open activity, walked back through the predecessor that lands latest; the network was not recalculated.",
        "fin_driver_flag_no": "The tool does not flag that row as critical, so read the path before quoting it.",
        "fin_driver_unlinked": "The last date in the file is on row {id}, {name}, {f}. No predecessor drives that row, so the date is the row's own and not the end of a logical path.",
        "fin_driver_changed": "In the previous delivery the date was held by another activity (row {id}, {name}): the path that drives the finish changed.",
        "fin_driver_same": "The same activity held the date in the previous delivery.",
        "cp": "{e} {e?activity|activities} entered the critical path and {l} left it, {lc} of those by finishing. Critical now: {n}, against {p} before.",
        "cp_none": "No activity entered or left the critical path. Critical now: {n}, against {p} before.",
        "cp_inserted": "{n} of the activities inserted this cycle {n?is|are} critical; {n?it is|they are} listed under scope.",
        "cp_fell": "{n} {n?unfinished activity|unfinished activities} lost a working day of float or more; the largest loss is {d} {d?day|days}, on row {id}.",
        "cp_fell_none": "No unfinished activity lost a working day of float or more.",
        "cp_basis_flag": "Read by the tool's own Critical flag.",
        "cp_basis_float": "The files carry no Critical flag, so critical here means total float at or below zero.",
        "cp_basis_mixed": "The two deliveries could not be read by the same criterion (one carries the Critical flag, the other does not); treat entries and exits with care.",
        "lg": "{a} {a?link|links} added, {r} removed, {l} with the lag changed and {t} with the type changed, between activities present in both deliveries.",
        "lg_none": "No link between activities present in both deliveries was edited.",
        "lg_scope": "A further {n} {n?link hangs|links hang} on inserted or removed activities: scope, not edited logic.",
        "lg_con": "Constraints on unfinished activities: {a} added, {c} changed and {r} removed.",
        "lg_con_none": "No constraint was added, changed or removed.",
        "lg_hard": "{n} of them {n?is|are} now hard (must start or finish on, or no later than): the date is pinned and the network stops deciding it.",
        "du": "{n} {n?activity|activities} with no actual start in either delivery had their duration edited: {up} longer and {down} shorter, a net {net} {net?working day|working days}. Nothing was executed on them; this is the plan rewritten.",
        "du_none": "No activity had its duration edited before starting.",
        "pr": "The past was rewritten on {n} {n?activity|activities}: {s} {s?actual start|actual starts} and {f} {f?actual finish|actual finishes} changed, and {p} {p?percent complete|percents complete} went down.",
        "pr_g": "The past was rewritten on {n} {n?activity|activities}: {s} {s?actual start|actual starts} and {f} {f?actual finish|actual finishes} changed, {p} {p?percent complete|percents complete} went down, and {g} {g?activity with recorded progress was|activities with recorded progress were} removed.",
        "pr_gone": "{n} {n?activity|activities} with recorded progress {n?was|were} removed from the schedule altogether, taking {v} of earned value with {n?it|them}; the largest is row {id} of the previous delivery, {name}, at {pct}%.",
        "pr_bl_item": "row {id}, {name}, {a} → {b}",
        "pr_baseline": "{n} of the changed actual dates now {n?falls|fall} exactly on the baseline date ({list}): the record was made to agree with the plan; ask for the evidence behind {n?it|them}.",
        "pr_removed": "{n} {n?actual date was|actual dates were} withdrawn altogether: work reported as started or finished last cycle is no longer recorded as such.",
        "pr_time": "{n} of the date changes {n?stays|stay} within the same day (time of day only); {n?it is|they are} listed last and {n?weighs|weigh} less.",
        "pr_ask": "Every figure the previous cycle reported on these activities rested on a record that no longer exists. Ask for each correction to be stated.",
        "pr_none": "No actual date changed and no percent complete went down: the past reads the same in both deliveries.",
        "ql": "Of the {t} {t?metric|metrics} computable in both deliveries, {w} worsened, {i} improved and {u} did not move.",
        "ql_bad": "Went from pass to fail: {list}.",
        "ql_good": "Went from fail to pass: {list}.",
        "ql_bei": "Baseline execution index: {a} before, {b} now.",
    },
    "pt": {
        "mv": "O avanço ponderado foi de {a}% para {b}%: {m} {m?ponto|pontos}. O avanço por atividade explica {x} deles e {r} não {r?é explicado|são explicados} por trabalho feito.",
        "mv_over": "O avanço ponderado foi de {a}% para {b}%: {m} {m?ponto|pontos}. O avanço por atividade soma {x}, mais que o movimento: {r} {r?ponto foi retirado|pontos foram retirados} por algo que não é trabalho feito.",
        "mv_terms": "A diferença tem nome: {list}.",
        "mv_terms_rest": "A diferença tem nome em parte: {list}; {r} {r?ponto fica|pontos ficam} sem explicação.",
        "term_rem_1": "{p} {p?ponto|pontos} do valor agregado apagado com uma atividade removida (linha {id} da entrega anterior, {name}, a {pct}%: {v})",
        "term_rem_n": "{p} {p?ponto|pontos} do valor agregado apagado com {n} atividades removidas ({v}; a maior é a linha {id} da entrega anterior, {name}, a {pct}%)",
        "term_ins": "{p} {p?ponto|pontos} do valor agregado de {n} {n?atividade inserida|atividades inseridas}",
        "term_chg": "{p} {p?ponto|pontos} de custo de linha de base alterado em {n} {n?atividade presente|atividades presentes} nas duas entregas",
        "term_bac": "{p} {p?ponto|pontos} do orçamento na conclusão, que foi de {a} para {b} ({parts})",
        "bac_ins": "+{v} de inseridas", "bac_rem": "−{v} de removidas", "bac_chg": "{v} de linhas de base alteradas",
        "mv_clean": "O avanço ponderado foi de {a}% para {b}%: {m} {m?ponto|pontos}, todos explicados pelo avanço por atividade.",
        "tr": "{e} {e?atividade moveu|atividades moveram} datas com datas reais por trás e {r} sem nenhuma; a própria linha de base se moveu em {b}.",
        "tr_none": "Nenhuma atividade moveu datas entre as duas entregas.",
        "sc": "{i} {i?atividade inserida|atividades inseridas} e {r} {r?removida|removidas}.",
        "sc_none": "Nenhuma atividade foi inserida ou removida: o escopo é o mesmo nas duas entregas.",
        "fin_later": "O término do projeto foi de {a} para {b}: {d} {d?dia corrido|dias corridos} mais tarde.",
        "fin_earlier": "O término do projeto foi de {a} para {b}: {d} {d?dia corrido|dias corridos} mais cedo.",
        "fin_same": "O término do projeto não se moveu: {b} nas duas entregas.",
        "fin_driver": "O que segura a data atual é a linha {id}, {name}, com término em {f}. É uma aproximação: a atividade em aberto que termina por último, percorrida para trás pela predecessora que chega mais tarde; a rede não foi recalculada.",
        "fin_driver_flag_no": "A ferramenta não marca essa linha como crítica, então leia o caminho antes de citá-lo.",
        "fin_driver_unlinked": "A última data do arquivo está na linha {id}, {name}, {f}. Nenhuma predecessora conduz essa linha, então a data é a da própria linha e não o fim de um caminho lógico.",
        "fin_driver_changed": "Na entrega anterior a data era segurada por outra atividade (linha {id}, {name}): o caminho que conduz o término mudou.",
        "fin_driver_same": "A mesma atividade segurava a data na entrega anterior.",
        "cp": "{e} {e?atividade entrou|atividades entraram} no caminho crítico e {l} {l?saiu|saíram}, {lc} delas por {lc?ter sido concluída|terem sido concluídas}. Críticas agora: {n}, contra {p} antes.",
        "cp_none": "Nenhuma atividade entrou ou saiu do caminho crítico. Críticas agora: {n}, contra {p} antes.",
        "cp_inserted": "{n} das atividades inseridas neste ciclo {n?é crítica|são críticas}; {n?está listada|estão listadas} em escopo.",
        "cp_fell": "{n} {n?atividade não concluída perdeu|atividades não concluídas perderam} um dia útil de folga ou mais; a maior perda é de {d} {d?dia|dias}, na linha {id}.",
        "cp_fell_none": "Nenhuma atividade não concluída perdeu um dia útil de folga ou mais.",
        "cp_basis_flag": "Lido pelo próprio campo Crítica da ferramenta.",
        "cp_basis_float": "Os arquivos não trazem o campo Crítica, então crítica aqui significa folga total menor ou igual a zero.",
        "cp_basis_mixed": "As duas entregas não puderam ser lidas pelo mesmo critério (uma traz o campo Crítica, a outra não); trate entradas e saídas com cuidado.",
        "lg": "{a} {a?vínculo incluído|vínculos incluídos}, {r} {r?removido|removidos}, {l} com a latência alterada e {t} com o tipo alterado, entre atividades presentes nas duas entregas.",
        "lg_none": "Nenhum vínculo entre atividades presentes nas duas entregas foi editado.",
        "lg_scope": "{n?Outro|Outros} {n} {n?vínculo está|vínculos estão} em atividades inseridas ou removidas: é escopo, não lógica editada.",
        "lg_con": "Restrições em atividades não concluídas: {a} {a?incluída|incluídas}, {c} {c?alterada|alteradas} e {r} {r?removida|removidas}.",
        "lg_con_none": "Nenhuma restrição foi incluída, alterada ou removida.",
        "lg_hard": "{n} delas agora {n?é rígida|são rígidas} (deve iniciar ou terminar em, ou não depois de): a data fica presa e a rede deixa de decidi-la.",
        "du": "{n} {n?atividade|atividades} sem início real em nenhuma das entregas {n?teve|tiveram} a duração editada: {up} mais {up?longa|longas} e {down} mais {down?curta|curtas}, saldo de {net} {net?dia útil|dias úteis}. Nada foi executado nelas; é o plano reescrito.",
        "du_none": "Nenhuma atividade teve a duração editada antes de iniciar.",
        "pr": "O passado foi reescrito em {n} {n?atividade|atividades}: {s} {s?início real|inícios reais} e {f} {f?término real|términos reais} mudaram, e {p} {p?percentual concluído caiu|percentuais concluídos caíram}.",
        "pr_g": "O passado foi reescrito em {n} {n?atividade|atividades}: {s} {s?início real|inícios reais} e {f} {f?término real|términos reais} mudaram, {p} {p?percentual concluído caiu|percentuais concluídos caíram} e {g} {g?atividade com avanço registrado foi removida|atividades com avanço registrado foram removidas}.",
        "pr_gone": "{n} {n?atividade com avanço registrado foi removida|atividades com avanço registrado foram removidas} do cronograma, levando {v} de valor agregado; a maior é a linha {id} da entrega anterior, {name}, a {pct}%.",
        "pr_bl_item": "linha {id}, {name}, {a} → {b}",
        "pr_baseline": "{n} das datas reais alteradas {n?passou|passaram} a coincidir exatamente com a linha de base ({list}): o registro foi ajustado ao plano; peça a evidência.",
        "pr_removed": "{n} {n?data real foi retirada|datas reais foram retiradas} por completo: trabalho informado como iniciado ou concluído no ciclo anterior não está mais registrado assim.",
        "pr_time": "{n} das mudanças de data {n?fica|ficam} dentro do mesmo dia (só o horário); {n?está listada|estão listadas} por último e {n?pesa|pesam} menos.",
        "pr_ask": "Todo número que o ciclo anterior informou sobre essas atividades se apoiava num registro que não existe mais. Peça que cada correção seja declarada.",
        "pr_none": "Nenhuma data real mudou e nenhum percentual concluído caiu: o passado lê igual nas duas entregas.",
        "ql": "Das {t} {t?métrica|métricas} calculáveis nas duas entregas, {w} {w?piorou|pioraram}, {i} {i?melhorou|melhoraram} e {u} não se {u?moveu|moveram}.",
        "ql_bad": "Passaram de atende para não atende: {list}.",
        "ql_good": "Passaram de não atende para atende: {list}.",
        "ql_bei": "Índice de execução da linha de base: {a} antes, {b} agora.",
    },
}

HARD_CONSTRAINT_CODES = {"MSO", "MFO", "SNLT", "FNLT"}


def half_up(v, d):
    """Round the way the report's renderer does: half away from zero on the
    shortest decimal form of the number. Python's `round` works on the binary
    value, so 0.9015 became 0,901 in a reading beside a tile showing 0,902."""
    q = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return float(q)


def fnum(v, d, lang):
    """A number the way the report's language writes it; never a negative zero.
    One rounding rule for every sentence, the same as the report's tiles."""
    if v is None:
        return "—"
    v = half_up(v, d)
    if v == 0:
        v = 0.0
    s = f"{v:,.{d}f}"
    if lang == "pt":
        s = s.replace(",", " ").replace(".", ",").replace(" ", ".")
    return s


def residual_parts(cmp_res: dict, lang: str) -> list:
    """The named terms of the movement residue, as phrases in the report's
    language, largest first. Empty when the comparison carries no terms (an
    older engine) or none of them is worth a hundredth of a point."""
    T = RC.get(lang, RC["en"])
    terms = cmp_res.get("residual_terms") or {}
    parts = []

    def pt(v):
        s = fnum(v, 2, lang)
        return s.replace("-", "−") if s.startswith("-") else "+" + s

    def money(v):
        return fnum(v, 0, lang)

    def fmt(key, **kw):
        return i18n.fmt(T[key], **kw)

    rem = terms.get("removed_earned") or {}
    if abs(rem.get("points") or 0) >= 0.005 and rem.get("rows"):
        top = rem["rows"][0]
        key = "term_rem_1" if len(rem["rows"]) == 1 else "term_rem_n"
        parts.append((rem["points"], fmt(key, p=pt(rem["points"]), n=fnum(len(rem["rows"]), 0, lang),
                                         v=money(rem["earned_erased"]), id=top["id"],
                                         name=top["name"], pct=fnum(top["percent"], 0, lang))))
    ins = terms.get("inserted_earned") or {}
    if abs(ins.get("points") or 0) >= 0.005:
        n = sum(1 for r in ins.get("rows") or [] if r.get("earned"))
        parts.append((ins["points"], fmt("term_ins", p=pt(ins["points"]), n=fnum(n, 0, lang))))
    chg = terms.get("baseline_cost_changed") or {}
    if abs(chg.get("points") or 0) >= 0.005:
        parts.append((chg["points"], fmt("term_chg", p=pt(chg["points"]),
                                         n=fnum(chg.get("count") or 0, 0, lang))))
    bac = terms.get("bac_change") or {}
    if abs(bac.get("points") or 0) >= 0.005:
        bits = []
        if bac.get("inserted_cost"):
            bits.append(fmt("bac_ins", v=money(bac["inserted_cost"])))
        if bac.get("removed_cost"):
            bits.append(fmt("bac_rem", v=money(bac["removed_cost"])))
        if abs(bac.get("changed_cost") or 0) >= 0.5:
            c = bac["changed_cost"]
            bits.append(fmt("bac_chg", v=("+" if c > 0 else "−") + money(abs(c))))
        parts.append((bac["points"], fmt("term_bac", p=pt(bac["points"]), a=money(bac["bac_before"]),
                                         b=money(bac["bac_after"]), parts=", ".join(bits))))
    parts.sort(key=lambda x: -abs(x[0]))
    return [p for _, p in parts]


def build_cycle(cmp_res: dict, lang: str, fmt_date, metric_title=None) -> dict:
    """Readings for the cycle report, keyed by section.

    `fmt_date` is the report's own date formatter, passed in so the sentences and
    the tables cannot disagree on how a date is written.
    """
    T = RC.get(lang, RC["en"])
    out: dict[str, list] = {}

    def add(section, key, **kw):
        try:
            out.setdefault(section, []).append(i18n.fmt(T[key], **kw))
        except (KeyError, ValueError, TypeError):
            pass

    def i(v):
        return fnum(v, 0, lang)

    # ---- movement, trend, scope
    prev, curr = cmp_res.get("previous") or {}, cmp_res.get("current") or {}
    mv, gap = cmp_res.get("movement_points"), cmp_res.get("movement_unexplained_points")
    if mv is not None:
        # The residue is stated as a size with a direction in words, never as
        # "-0,33 are not explained", which reads as a count gone negative.
        args = dict(a=fnum(prev.get("percent_earned"), 2, lang),
                    b=fnum(curr.get("percent_earned"), 2, lang), m=fnum(mv, 2, lang),
                    x=fnum(cmp_res.get("decomposition_sums_to_points"), 2, lang),
                    r=fnum(abs(gap or 0), 2, lang))
        if abs(gap or 0) < 0.01:
            add("movement", "mv_clean", **args)
        else:
            add("movement", "mv" if gap > 0 else "mv_over", **args)
            parts = residual_parts(cmp_res, lang)
            rest = cmp_res.get("residual_remainder_points")
            if parts and rest is not None and abs(rest) < 0.01:
                add("movement", "mv_terms", list="; ".join(parts))
            elif parts and rest is not None:
                add("movement", "mv_terms_rest", list="; ".join(parts), r=fnum(abs(rest), 2, lang))
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
    if drv and fc.get("driver_linked") is False:
        add("c1", "fin_driver_unlinked", id=drv["id"], name=drv["name"], f=fmt_date(drv.get("finish"), lang))
    elif drv:
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
            gone = pr.get("removed_with_progress") or []
            add("c5", "pr_g" if gone else "pr", n=i(pr["activities"]), s=i(len(pr["actual_start"])),
                f=i(len(pr["actual_finish"])), p=i(len(pr["percent_decreased"])), g=i(len(gone)))
            if gone:
                add("c5", "pr_gone", n=i(len(gone)), v=fnum(sum(g["earned_erased"] for g in gone), 0, lang),
                    id=gone[0]["id"], name=gone[0]["name"], pct=fnum(gone[0]["percent"], 0, lang))
            on_bl = [r for r in pr["actual_start"] + pr["actual_finish"] if r.get("matches_baseline")]
            if on_bl:
                add("c5", "pr_baseline", n=i(len(on_bl)), list="; ".join(
                    i18n.fmt(T["pr_bl_item"], id=r["id"], name=r["name"],
                             a=fmt_date(r["before"], lang), b=fmt_date(r["after"], lang))
                    for r in on_bl[:5]))
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
