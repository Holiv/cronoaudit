# cronoaudit

[English](README.md)

**A cronoaudit revisa cronogramas de obras e de infraestrutura.** Você entrega o XML exportado
do cronograma e ela diz o que merece atenção. Ela procura as falhas que produzem um número
errado com cara de certo, e não uma mensagem de erro. Exemplos:
- uma atividade que começou antes de a predecessora terminar;
- uma data real reescrita depois do fato;
- um marco a um dia da data limite;
- uma atividade cujos dois percentuais de avanço não batem.

Ela funciona de dois jeitos:

- **Com um agente de IA**, numa conversa. Você pergunta com suas palavras ("analise este
  cronograma", "compare estas duas versões", "de onde veio o atraso?") e o agente responde
  usando a cronoaudit. Use o agente de sua preferência, ou o que a sua empresa permite no seu
  computador. Este guia cobre quatro: Claude Code, GitHub Copilot, Codex (OpenAI) e Grok Build
  (xAI). Qualquer agente que leia o formato aberto [Agent Skills](https://agentskills.io) também
  funciona.
- **Sem agente nenhum.** Um comando gera o mesmo relatório, e nada sai do seu computador.

Os números nunca vêm do agente. Vêm do motor da cronoaudit: scripts em Python que rodam no seu
computador, leem o XML e calculam cada número sempre do mesmo jeito. O agente cita esses
números; não inventa.

## O que você recebe

Um relatório HTML que abre no navegador, no idioma do próprio cronograma (português ou inglês).
Cada seção abre com uma leitura curta escrita por regras, não pelo agente.

**Para uma entrega:**
- o prazo primeiro: cada marco contra a sua data limite, com a margem e onde nasce o atraso;
- nove verificações de integridade, a rede primeiro;
- a curva S com os dados do próprio arquivo, conciliada ao centavo com os números da ferramenta;
- produtividade e tendência por recurso;
- catorze métricas de qualidade da rede;
- Earned Schedule e as próximas semanas;
- forense que aponta onde entrou o atraso de cada marco.

**Para duas versões do mesmo cronograma, na ordem em que se lê:**
1. prazo;
2. se a medição é confiável;
3. o que o plano mudou;
4. avanço;
5. folga e caminho crítico;
6. qualidade da rede;
7. uma lista do que cobrar da contratada, um item por evidência.

## Antes de começar

Você precisa de três coisas:

1. **Um computador com Windows, macOS ou Linux.** Este guia mostra o Windows primeiro, porque
   é onde vive a maioria dos cronogramas.
2. **O cronograma em XML.** No MS Project: **Arquivo → Salvar como → Formato XML (\*.xml)**. É o
   formato do próprio Project; nada do que a cronoaudit precisa se perde. Salve numa pasta só
   para ele.
3. **Opcional: um agente de IA.** Só se você quiser a conversa. Cada agente precisa de uma
   conta no fornecedor; confira qual plano inclui o agente, e confira a política da sua empresa
   antes de usar um com cronograma da empresa (veja [Para onde vão os seus dados](#para-onde-vão-os-seus-dados)).

Não é preciso saber programar. Você vai copiar e colar alguns comandos.

### Como abrir o PowerShell (Windows)

1. Aperte a tecla Windows.
2. Digite `PowerShell`.
3. Clique em **Windows PowerShell**.

Abre uma janela com um cursor piscando. Cole o comando ali com o botão direito do mouse e
aperte Enter. Use essa janela, não o "Prompt de Comando" (cmd): os comandos abaixo são para o
PowerShell.

No macOS, abra o **Terminal** (Aplicativos → Utilitários).

## Passo 1: instalar a cronoaudit

Um comando instala a cronoaudit para todos os agentes de uma vez, e também para usar sem agente.

**Windows (PowerShell):**

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
```

**macOS / Linux (Terminal):**

```
curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
```

O que deve aparecer no fim: **`cronoaudit 0.8.0 is installed`**.

Sobre o Python: a cronoaudit precisa do Python 3.9 ou mais novo, e de mais nada. No Windows, se
o computador não tiver Python, o instalador traz uma cópia própria do python.org, usada só pela
cronoaudit, sem precisar de administrador. No macOS e no Linux o Python normalmente já existe.

Para atualizar depois, rode o mesmo comando de novo.

## Passo 2: instalar um agente (pule se não for usar)

Escolha um. Cada bloco é o comando oficial do fornecedor, em novembro de 2026. Depois de
instalar, feche o PowerShell e abra outro, para o comando novo ser encontrado.

### Claude Code (Anthropic)

```
irm https://claude.ai/install.ps1 | iex
```

macOS / Linux: `curl -fsSL https://claude.ai/install.sh | bash`. Abra com `claude` e siga o
login. Guia oficial: [code.claude.com](https://code.claude.com/docs/en/setup).

### GitHub Copilot CLI

```
winget install GitHub.Copilot
```

Abra com `copilot` e entre com a sua conta do GitHub. Precisa de um plano do Copilot. Se o seu
Copilot vem da empresa, é a empresa que decide se a CLI está habilitada. Guia oficial, com as
opções para macOS e Linux:
[docs.github.com](https://docs.github.com/pt/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli).

### Codex (OpenAI)

```
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

macOS / Linux: `curl -fsSL https://chatgpt.com/codex/install.sh | sh`. Abra com `codex` e entre
com a sua conta do ChatGPT. Guia oficial: [github.com/openai/codex](https://github.com/openai/codex).

### Grok Build (xAI)

```
irm https://x.ai/cli/install.ps1 | iex
```

macOS / Linux: `curl -fsSL https://x.ai/cli/install.sh | bash`. Abra com `grok` e faça o login.
Guia oficial: [docs.x.ai](https://docs.x.ai/build/overview).

### O agente enxerga a cronoaudit?

Os quatro leem a pasta de skills que o instalador criou (`.agents\skills` na sua pasta de
usuário; o Claude Code lê `.claude\skills`, que o instalador também preenche). Para conferir,
abra o agente e pergunte *"quais skills você tem?"*. A cronoaudit deve aparecer na resposta. No
Copilot dá também para digitar `/skills list`; no Grok, `/skills`.

## Passo 3: analisar um cronograma

1. No PowerShell, vá para a pasta onde está o XML. O jeito mais fácil: digite `cd ` com um
   espaço depois, arraste a pasta do Explorer para a janela e aperte Enter.
2. Abra o seu agente: `claude`, `copilot`, `codex` ou `grok`.
3. Escreva o que você quer, com as suas palavras. Por exemplo:
   - *Analise o cronograma rodovia-rev04.xml.*
   - *Compare rodovia-rev03.xml com rodovia-rev04.xml e me diga o que mudou.*
   - *Quais marcos correm risco de passar da data limite?*
   - *Escreva a síntese e gere o relatório final.*

O agente roda a cronoaudit, lê os resultados e responde. O relatório fica salvo ao lado do XML e
abre no navegador. Você pode continuar perguntando sobre qualquer atividade, marco ou número.

Uma coisa que confunde: comandos que começam com `/` (como `/skills`) são digitados **dentro**
do agente, depois de abri-lo. Digitados direto no PowerShell, não fazem nada.

### Como é uma conversa

De um teste com a rodovia fictícia que vem com a cronoaudit ([`examples/`](examples/)):

> **Você:** Compare a rev03 com a rev04 e me diga o que mudou, por assunto.
>
> **Agente:** O término do projeto foi de 04/10/2027 para 25/10/2027, 21 dias depois. Antes do
> avanço, três pontos pedem resposta da contratada: o término real da linha 29 foi reescrito e
> passou a coincidir com a data da linha de base; a linha 119, a 100%, foi removida e levou o
> valor agregado junto; e a linha de base da linha 132 mudou. O atraso do marco do viaduto nasce
> na linha 148 e cresce na linha 157, cuja duração passou de 12 para 20 dias…

Cada número dessa resposta vem dos arquivos do motor. O agente também aponta quando uma leitura
automática não se encaixa nos dados, e mostra os números.

## Sem agente nenhum

Rode o motor você mesmo. Nada sai do seu computador:

```
python "$env:USERPROFILE\.claude\skills\cronoaudit\scripts\review.py" "C:\caminho\do\cronograma.xml"
```

Dois arquivos, o anterior primeiro, geram o relatório de comparação. No macOS e no Linux, use
`python3` e `~/.claude/skills/cronoaudit/scripts/review.py`.

No Windows, use `python` (ou `py`), não `python3`: ali o `python3` costuma ser um atalho para a
Microsoft Store que não roda nada.

## Para onde vão os seus dados

- **O motor roda no seu computador e não envia nada.** Ele não usa a rede.
- **O instalador baixa** este repositório do GitHub e, no Windows e só se precisar, o Python do
  python.org. Mais nada.
- **O agente é outra história.** O que o agente lê (o XML, o relatório, as suas perguntas) vai
  para o fornecedor dele, nos termos da sua conta ou da conta da empresa. Confira a política da
  empresa antes de usar um agente com cronograma de contrato.
- **Se a política diz que não pode usar agente,** use a cronoaudit sem ele: mesmo relatório, sem
  conversa.

### Modo secreto (experimental)

Para quando você quer a conversa, mas os nomes, os valores e as datas devem ficar no seu
computador. Você mesmo roda um comando:

```
python "$env:USERPROFILE\.claude\skills\cronoaudit\scripts\review.py" "C:\caminho\do\cronograma.xml" --secret
```

A cronoaudit analisa o arquivo real no seu computador e grava uma cópia codificada numa pasta
separada:
- os nomes das atividades viram códigos como `T·3fa91c`;
- as datas viram contagens de dias como `D+0412`;
- os valores em dinheiro são multiplicados por um fator secreto.

Durações, percentuais, índices e números de linha continuam reais, então a análise continua
fazendo sentido. Você abre o agente nessa pasta, e ele lê só a cópia codificada. Quando você
pede o relatório final, a cronoaudit decodifica no seu computador e abre com os nomes reais.

O que ele faz e o que não faz:
- No Claude Code, a pasta também traz regras que mantêm o agente dentro dela. Os outros agentes
  recebem as mesmas regras como instruções escritas.
- Os códigos não tornam o cronograma anônimo: a estrutura, as durações e os números de linha
  continuam legíveis.
- Não substitui a política da sua empresa sobre serviços de IA.

Testado no Windows com o Claude Code em 22/11/2026, e num cronograma real de 6.484 tarefas:
nenhum nome, data ou valor real chegou à cópia codificada.

## Se algo der errado

| O que aparece | O que fazer |
|---|---|
| *'irm' não é reconhecido* | Você está no Prompt de Comando (cmd). Abra o PowerShell (veja acima). |
| *python não é reconhecido* | Rode o instalador da cronoaudit de novo; no Windows ele traz o próprio Python. Ou instale o Python do python.org e marque **Add python.exe to PATH**. |
| O comando do agente (`claude`, `copilot`…) não é encontrado | Feche o PowerShell e abra outro. |
| O agente não conhece a cronoaudit | Feche o agente e abra de novo. No Copilot, `/skills reload`. Confira com *"quais skills você tem?"*. |
| `/cronoaudit` não faz nada | Comandos com `/` só funcionam dentro do agente, não no PowerShell. Você também pode só pedir com palavras. |

## Mais

- **O processo inteiro, passo a passo** (em inglês):
  [`skills/cronoaudit/references/usage.md`](skills/cronoaudit/references/usage.md).
- **Manual**, catorze capítulos, dos conceitos ao glossário: português
  [`docs/manual/manual-pt.pdf`](docs/manual/manual-pt.pdf), inglês
  [`docs/manual/manual-en.pdf`](docs/manual/manual-en.pdf).
- **Suplemento para o MS Project (Windows, beta).** Botões no Project que exportam o cronograma
  aberto e iniciam a análise. É um atalho, não uma exigência: [`msproject/`](msproject/LEIA-ME.md).
- **Um exemplo fictício** para experimentar primeiro, com a lista do que foi plantado nele:
  [`examples/`](examples/LEIA-ME.md).

### Outras formas de instalar

| Caminho | Comando |
|---|---|
| Qualquer cliente de Agent Skills | `npx skills add Holiv/cronoaudit -g` |
| Claude Code, como plugin | `/plugin marketplace add Holiv/cronoaudit`, depois `/plugin install cronoaudit@cronoaudit` |
| Codex | `$skill-installer https://github.com/Holiv/cronoaudit` |
| Uma equipe, pelo projeto | `git clone https://github.com/Holiv/cronoaudit .agents/skills/cronoaudit` dentro do projeto |

Onde o instalador coloca: `.claude/skills/cronoaudit` e `.agents/skills/cronoaudit` na sua pasta
de usuário. No macOS e no Linux, `--only claude` ou `--only agents` escolhe uma só.

As opções do instalador no Windows são definidas na mesma janela do PowerShell, antes do comando:

| Opção | Comando |
|---|---|
| Nunca baixar Python; parar se não houver | `$env:CRONOAUDIT_NO_PYTHON="1"` |
| Usar o Python próprio mesmo se o computador tiver um | `$env:CRONOAUDIT_EMBED_PYTHON="1"` |
| Instalar de outra branch | `$env:CRONOAUDIT_REF="nome-da-branch"` |

### O que ela não faz

Não lê Primavera P6. Não produz pleito contratual de atraso: a forense mostra o mecanismo, e um
pleito precisa de registros contemporâneos e de um método formal. Não certifica DCMA: as
catorze métricas são uma implementação, identificada como tal. Nunca inventa um número que o
arquivo não trouxe, e marca cada afirmação como `medido`, `inferido` ou `relatado`.

### Conferir a ferramenta

`python skills/cronoaudit/scripts/test_checks.py`, a partir de uma cópia deste repositório. Cada
verificação precisa disparar no caso positivo e ficar em silêncio no negativo.

### Procedência

Escrita a partir de um método documentado e genérico, sem portar o código de nenhuma aplicação,
e medida num programa real de 6.484 tarefas com 107 calendários. Números de escala ficam;
identidades saem: nenhum empregador, contratada, contrato, quilometragem, pessoa ou valor
aparece neste repositório.

### Licença

Apache 2.0. © 2026 Helton da Silva de Oliveira.
