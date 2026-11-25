# Exemplo: uma obra rodoviária fictícia, duas entregas

English: [README.md](README.md)

Duas fotografias do mesmo cronograma, com um mês de intervalo, para experimentar o
cronoaudit em algo que se lê como uma obra rodoviária de verdade:

| Arquivo | Data de status | Papel |
|---|---|---|
| `rodovia-ficticia-rev03.xml` | 30/09/2026 | entrega anterior |
| `rodovia-ficticia-rev04.xml` | 30/10/2026 | entrega atual |

**Tudo neles é inventado.** A rodovia (RF-140), o trecho (km 12+000 ao km 36+000), o
contratante, a contratada, as quantidades, os preços unitários e todas as datas foram
criados para este exemplo. Nenhuma obra, empresa, contrato ou lugar real está
representado.

## O que há no cronograma

- 142 atividades sob 32 linhas de resumo, cerca de 220 vínculos, 38 recursos, nomes em
  português.
- EAP por trecho e disciplina: marcos contratuais, mobilização, quatro segmentos de
  6 km (terraplenagem, drenagem, pavimentação, sinalização, iluminação), um viaduto,
  desmobilização.
- Dois calendários, ambos com os feriados nacionais e uma reserva de chuva de dezembro
  a março: o da obra (cinco dias) e o de terraplenagem (seis dias). Cada recurso tem
  ainda o seu próprio calendário, derivado de um dos dois — é como o MS Project grava
  um recurso e o que ele espera ao abrir o arquivo.
- Nove marcos, todos com data limite.
- Linha de base com custo (preço unitário vezes quantidade), **distribuído no tempo**,
  um bloco por dia útil, de modo que previsto até a data, SV, IDP e Earned Schedule
  são calculáveis. O dinheiro fica em centésimos, como o formato XML guarda: um
  orçamento de 17.499.283.800 num arquivo de dados é R$ 174.992.838,00.
- Dois campos personalizados, `DISCIPLINA` e `SEGMENTO`, para o `--group-by`.

A maior parte está saudável de propósito. Datas, folgas e a marca de crítica saem de
um cálculo de ida e volta sobre os vínculos e os calendários, então concordam com a
lógica.

## Como rodar

Depois de instalar, o caminho mais curto: o instalador copia estes arquivos para a pasta
`cronoaudit-exemplo`, na sua pasta de usuário, e este comando roda a comparação e abre o
relatório no navegador:

```
python3 ~/.claude/skills/cronoaudit/scripts/review.py --example
```

No Windows, use a linha que o instalador mostrou no fim, a que termina em `--example`. A partir
de uma cópia do repositório:

```
python3 skills/cronoaudit/scripts/review.py \
    examples/rodovia-ficticia-rev03.xml examples/rodovia-ficticia-rev04.xml \
    --outdir out --lang pt
```

Com `--group-by DISCIPLINA` o avanço é pesado por disciplina em vez de por segmento.
Um arquivo sozinho dá a análise daquela entrega; a rev03 sozinha sai limpa.

Para ver no MS Project: Arquivo > Abrir, escolha o XML, "Abrir como novo projeto".

## O que foi plantado, e onde o relatório mostra

Os números de linha são os da rev04.

| # | Plantado | Onde aparece |
|---|---|---|
| 1 | Avanço real em outubro em uma dúzia de atividades | Ciclo: datas movidas com datas reais por trás (execução); realizado de 23,44% para 28,01% |
| 2 | Linha 63, *Sarjetas e valetas — Seg. 2*: início preso em 28/12/2026 por uma restrição "não iniciar antes de", 46 dias depois do que estava na rev03, sem nada executado | Ciclo: replanejamento; lógica, uma restrição incluída |
| 3 | Linha 36, *Imprimação — Seg. 1*, iniciada em 29/10 com a linha 35, *Base de brita graduada — Seg. 1*, ainda aberta | Achado A1, fora de sequência, as duas pontas marcadas |
| 4 | As linhas 77, 89, 136 e 170 não têm sucessora | Qualidade da rede Q1 (4 de 96, abaixo do limiar, então a rede é lida como vinculada) |
| 5 | As mesmas quatro, mais a linha 57 inserida, carregam de 79 a 205 dias de folga | Qualidade da rede Q6 |
| 6 | Linha 55, *Aterro compactado — Seg. 2*: 95% concluída pela duração, 57% físico | Curva S: o outro método de valor agregado leria 0,44 ponto a mais, e a leitura nomeia a linha 55 como 100% da diferença; produtividade: medição inconsistente |
| 7 | Linha 29, *Bueiros tubulares — Seg. 1*: o término real era 05/06/2026 na rev03 e aparece como 01/06/2026, a data da linha de base, na rev04 | Ciclo: passado reescrito, um término real |
| 8 | Um vínculo incluído (linha 106 depois da 94) e um removido (a linha 127 deixou de depender da 123) | Ciclo: lógica |
| 9 | Linha 157, *Lançamento das vigas pré-moldadas*: 12 dias viraram 20, sem ter iniciado | Ciclo: duração alterada em atividade não iniciada |
| 10 | Linha 132, *CBUQ capa de rolamento — Seg. 4*: linha de base deslocada quatro semanas | Ciclo: a referência se moveu; aviso sobre a base de comparação |
| 11 | A linha 57, *Contenção em gabião*, só existe na rev04; *Remanejamento de cercas — Seg. 4* só na rev03 | Ciclo: escopo, 1 inserida e 1 removida; 0,33 ponto do movimento não explicado por avanço |
| 12 | A folga até o marco *Liberação ao tráfego — Segmento 3* caiu de 13 para 3 dias | Ciclo: caminho crítico, folga perdida; a forense nomeia a origem |
| 13 | O término do projeto foi de 04/10/2027 para 25/10/2027, pelo viaduto | Ciclo: término do projeto e a cadeia que o segura; forense: origem nas estacas, ampliada pela linha 157 |
| 14 | A pavimentação é cerca de dois terços do que falta, e metade do custo remanescente cai entre dezembro e março | Olhando adiante: exposição à chuva, 50% em meses reservados, 52% se tudo escorregar trinta dias |

Também estão lá sem terem sido plantados, porque um cronograma atrasado os tem: IDP de
0,90, índice de execução da linha de base de 0,65 e quatro semanas à frente que o ritmo
praticado não alcança.

## Abrir no MS Project muda parte disto

O Project recalcula o cronograma ao abrir o XML e de novo ao salvar como `.mpp`. O que
ele mantém e o que ele recalcula decidem quais achados sobrevivem.

- **Mantidos** (itens 2, 3, 4, 6, 7, 8, 9, 10, 11): datas reais, percentual concluído
  e percentual físico, vínculos, restrições, durações, datas da linha de base e datas
  limite, as linhas inserida e removida.
- **Dependem do arquivo como exportado** (itens 5, 12, 13, 14 e os números do 1): datas
  de tendência, folga total, a marca de crítica, os campos de valor agregado e o custo
  da linha de base distribuído no tempo. Depois de um recálculo eles são do Project, não
  do gerador, e podem diferir em dias, sobretudo em torno da atividade fora de
  sequência.

Para reproduzir o relatório como descrito, rode os dois XML como estão.

## Como regenerar

```
python3 examples/make_exemplo.py
```

Só biblioteca padrão, determinístico: os mesmos dois arquivos, byte a byte. O que
aconteceu em cada mês e cada problema plantado estão declarados no topo do script
(`PERTURB`, `PLANTED`). `python3 skills/cronoaudit/scripts/test_checks.py` confere que
os arquivos são o que o gerador escreve e que todos os itens acima são encontrados.
