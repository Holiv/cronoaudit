#!/usr/bin/env python3
"""Problem, impact and solution, per finding, per language.

This is what turns a count into something a reader can act on, and what lets the
report be handed to somebody who was not in the room. A number with no
consequence attached gets filed. Each entry is a triple: (problem, impact,
solution). The finding code is the stable identifier; these are the words.
"""
from __future__ import annotations

EXPLAIN = {
    "en": {
        "A1": (
            "A successor has started while its predecessor has not finished, or finished "
            "after the successor started by more than the link allows. The logic in the "
            "file says one follows the other; the works did not.",
            "Once the tool recalculates over a network the works does not follow, every "
            "forecast date is computed from a false premise. A second effect flatters the "
            "schedule: delay on stalled predecessors stops propagating to the milestones, "
            "because the successors were already delivered. The plan looks healthy at the "
            "end precisely because it is broken in the middle.",
            "Settle these before discussing any date. Either the link is wrong and should be "
            "corrected, or the sequence was genuinely broken on site and the consequence "
            "belongs in the forecast. Do not delete the link to silence the warning: that "
            "discards the only record that the order was not followed.",
        ),
        "A2": (
            "A successor is complete while its predecessor has never started. This is the "
            "extreme form of a broken sequence.",
            "It is unanswerable in a meeting. It usually means the sequence was invented for "
            "the plan and never reflected how the work is done, or the reporting landed on "
            "the wrong activity. Either way the schedule is worth less as a forecast.",
            "Check each pair individually and record, per pair, whether the link is fiction "
            "or the reporting is wrong. The answer differs between pairs, and assuming one "
            "cause for all of them is how the real one gets missed.",
        ),
        "H": (
            "A trend date is in the past relative to the status date with no actual behind "
            "it: a start with no actual start, or a finish with no actual finish. The plan "
            "says it happened; nothing in the file says it did.",
            "Every successor is being forecast from a date that already did not hold. The "
            "error compounds down the chain, and because each date still looks plausible, "
            "nothing in the file announces it.",
            "Two possibilities needing different answers: the work happened and was not "
            "reported, or it did not happen and the forecast has to move. Enter the actual "
            "dates for the first; reschedule honestly for the second. Leaving it is the only "
            "wrong option.",
        ),
        "E": (
            "The forecast finish moved earlier than the baseline by more than the threshold, "
            "and the activity has never started.",
            "Progress pulled forward with no execution behind it is a plan change dressed as "
            "performance. Aggregated, it offsets real delay elsewhere and produces an overall "
            "figure that looks healthy while nothing has started where the money is.",
            "Ask what changed to justify the earlier date. If nothing did, the forecast is "
            "optimistic and should go back. If something did, record it, so the next cycle "
            "compares against a reference somebody agreed to.",
        ),
        "C": (
            "The forecast finish moved later than the baseline by more than the threshold. "
            "Completed activities stay in the list on purpose: consumed delay is information.",
            "This is the finding the other party expects and the easiest to argue about, which "
            "is why it needs the reproduction attached. Its weight matters more than its "
            "count: the same number of delayed activities means something very different "
            "depending on the share of budget they carry.",
            "Read it next to the weight distribution, never alone, and bring the reproduction "
            "to the meeting. Establish whether the slippage is contained or propagating to a "
            "contractual milestone; the float column says how much room is left.",
        ),
        "G": (
            "The duration does not match the working time between start and finish, measured "
            "on the activity's own calendar.",
            "It does not say what is wrong, only that something was edited inconsistently: a "
            "start anchored on an actual date with the remainder pushed after the last "
            "predecessor, a typed date over a calculated one, a constraint fighting the "
            "logic. Reported alone it produces argument, not agreement.",
            "Use it to choose what to inspect, never as a finding in its own right. Look at the "
            "largest gaps first: a gap of days is usually a rounded duration, a gap of months "
            "is a date that was forced.",
        ),
        "B": (
            "A milestone has no deadline set, so nothing in the file makes its date binding.",
            "Without a deadline the milestone shows comfortable float even after the "
            "contractual date has passed. The schedule reports no problem because it was "
            "never told the date mattered. A deadline is not a constraint: it moves nothing, "
            "it only reveals slippage, so its absence hides the slippage rather than causing it.",
            "Set the contractual dates as deadlines on the milestones that carry them. It "
            "changes no calculation and makes every later report tell the truth about float.",
        ),
        "F": (
            "The activity has an actual start, no actual finish, and percent complete at zero.",
            "Work in progress that reports nothing is invisible to every aggregate, and the "
            "activity cannot be told apart from one that started and stalled.",
            "Enter a percentage, even an approximate one, or remove the actual start if the "
            "work has not really begun. An approximate number that gets reviewed beats a zero "
            "that gets believed.",
        ),
        "P": (
            "The activity reports one hundred percent physical complete with no actual finish "
            "date.",
            "A record-keeping defect, not an execution defect, and the distinction decides who "
            "the conversation is with. Left among the network findings it accuses the crew of "
            "working out of sequence when the work was done and only the date is missing.",
            "Enter the actual finish. Until then the activity is deliberately excluded from "
            "the network findings, so that a reporting problem is not reported as an "
            "execution problem.",
        ),
    },
    "pt": {
        "A1": (
            "Uma sucessora começou enquanto a predecessora não terminou, ou terminou depois "
            "do início da sucessora além do que o vínculo permite. A lógica do arquivo diz "
            "que uma segue a outra; a obra não seguiu.",
            "Depois que a ferramenta recalcula sobre uma rede que a obra não segue, toda data "
            "de tendência é calculada sobre premissa falsa. Um segundo efeito embeleza o "
            "cronograma: o atraso das predecessoras paradas deixa de propagar para os "
            "marcos, porque as sucessoras já foram entregues. O plano parece saudável no fim "
            "justamente porque está quebrado no meio.",
            "Resolva antes de discutir qualquer data. Ou o vínculo está errado e deve ser "
            "corrigido, ou a sequência foi realmente quebrada em campo e a consequência tem "
            "de entrar na tendência. Não apague o vínculo para calar o aviso: isso descarta o "
            "único registro de que a ordem não foi cumprida.",
        ),
        "A2": (
            "Uma sucessora está concluída e a predecessora nunca começou. É a forma extrema "
            "de sequência quebrada.",
            "É irrespondível numa reunião. Normalmente significa que a sequência foi "
            "inventada para o plano e nunca refletiu como o serviço é executado, ou que o "
            "apontamento caiu na atividade errada. Nos dois casos o cronograma vale menos "
            "como previsão.",
            "Confira par por par e registre, em cada um, se o vínculo é ficção ou se o "
            "apontamento está errado. A resposta varia entre os pares, e supor uma causa "
            "única para todos é como a verdadeira passa batida.",
        ),
        "H": (
            "Uma data de tendência está no passado em relação à data de status sem "
            "realização por trás: início sem início real, ou término sem término real. O "
            "plano diz que aconteceu; nada no arquivo diz que aconteceu.",
            "Toda sucessora está sendo projetada a partir de uma data que já não se "
            "sustentou. O erro acumula pela cadeia e, como cada data continua plausível, "
            "nada no arquivo denuncia.",
            "Duas possibilidades com respostas diferentes: o serviço aconteceu e não foi "
            "apontado, ou não aconteceu e a tendência tem de andar. Lance as datas reais no "
            "primeiro caso; reprograme com honestidade no segundo. Deixar como está é a "
            "única opção errada.",
        ),
        "E": (
            "O término de tendência andou para antes da linha de base além do limiar, e a "
            "atividade nunca começou.",
            "Avanço puxado para antes sem execução por trás é mudança de plano vestida de "
            "desempenho. Agregado, compensa atraso real em outro lugar e produz um número "
            "global saudável enquanto nada começou onde está o dinheiro.",
            "Pergunte o que mudou para justificar a data mais cedo. Se nada mudou, a "
            "tendência está otimista e deve voltar. Se algo mudou, registre, para o ciclo "
            "seguinte comparar contra uma referência que alguém acordou.",
        ),
        "C": (
            "O término de tendência andou para depois da linha de base além do limiar. "
            "Atividades concluídas ficam na lista de propósito: atraso consumado é informação.",
            "É o achado que a outra parte espera e o mais fácil de contestar, e é por isso "
            "que precisa da reprodução anexada. O peso importa mais que a contagem: o mesmo "
            "número de atividades atrasadas significa coisas muito diferentes conforme a "
            "fatia de orçamento que carregam.",
            "Leia junto com a distribuição de peso, nunca isolado, e leve a reprodução para a "
            "reunião. Estabeleça se o escorregão está contido ou se propaga até um marco "
            "contratual; a coluna de folga diz quanta margem resta.",
        ),
        "G": (
            "A duração não casa com o tempo útil entre início e término, medido no calendário "
            "da própria atividade.",
            "Não diz o que está errado, apenas que algo foi editado de forma inconsistente: "
            "início ancorado na data real com o remanescente empurrado para depois da última "
            "predecessora, data digitada sobre data calculada, restrição brigando com a "
            "lógica. Reportado sozinho, produz discussão em vez de acordo.",
            "Use para escolher o que inspecionar, nunca como achado próprio. Olhe primeiro as "
            "maiores diferenças: diferença de dias costuma ser duração arredondada, "
            "diferença de meses é data que foi forçada.",
        ),
        "B": (
            "O marco não tem Data Limite preenchida, então nada no arquivo torna a data dele "
            "vinculante.",
            "Sem Data Limite o marco exibe folga confortável mesmo com a data contratual "
            "vencida. O cronograma não reporta problema porque nunca foi informado de que a "
            "data importava. Data Limite não é restrição: não move nada, só revela "
            "escorregão, então a ausência dela esconde o escorregão em vez de causá-lo.",
            "Cadastre as datas contratuais como Data Limite nos marcos que as têm. Não muda "
            "nenhum cálculo e faz todo relatório seguinte dizer a verdade sobre folga.",
        ),
        "F": (
            "A atividade tem início real, não tem término real, e o percentual concluído é "
            "zero.",
            "Serviço em andamento que não reporta nada é invisível para todo agregado, e a "
            "atividade fica indistinguível de uma que começou e parou.",
            "Lance um percentual, mesmo aproximado, ou remova o início real se o serviço não "
            "começou de fato. Número aproximado que é revisado vale mais que zero em que se "
            "acredita.",
        ),
        "P": (
            "A atividade reporta cem por cento físico sem data de término real.",
            "Defeito de registro, não de execução, e a distinção decide com quem é a "
            "conversa. Mantida entre os achados de rede, acusa a equipe de executar fora de "
            "sequência quando o serviço foi feito e só falta a data.",
            "Lance o término real. Até então a atividade é deliberadamente excluída dos "
            "achados de rede, para que um problema de apontamento não seja reportado como "
            "problema de execução.",
        ),
    },
}


def explain(lang: str) -> dict:
    return EXPLAIN.get(lang, EXPLAIN["en"])
