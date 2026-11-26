# cronoaudit

[English](README.md)

![cronoaudit: auditoria de cronograma de obra, no seu computador. Um motor local em Python e uma Agent Skill para o seu agente de IA.](docs/img/pt/banner.png)

![versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-1f6feb)
![licença](https://img.shields.io/badge/licen%C3%A7a-Apache%202.0-555)
![Windows · macOS · Linux](https://img.shields.io/badge/Windows%20%C2%B7%20macOS%20%C2%B7%20Linux-roda-2ea043)
![dados](https://img.shields.io/badge/motor-n%C3%A3o%20usa%20a%20rede-2ea043)

**A cronoaudit revisa cronogramas de obras e de infraestrutura feitos no MS Project e diz o que
merece atenção.** Ela procura as falhas que produzem um número errado com cara de certo, e não uma
mensagem de erro:
- um marco a um dia da data limite;
- uma data real reescrita depois do fato;
- uma atividade com avanço que sumiu de uma revisão para a outra;
- uma atividade que começou antes de a predecessora terminar.

É uma Agent Skill de código aberto, com um motor local em Python. Você usa do jeito que preferir:
conversando com um agente de IA, clicando num botão dentro do MS Project, ou rodando sem IA
nenhuma. O motor roda no seu computador e não envia nada.

<p align="center">
<img src="docs/img/pt/demo.gif" alt="Demonstração: um comando compara duas revisões do exemplo fictício no terminal, depois o relatório abre e rola dos alertas até as cobranças para a contratada" width="640">
</p>

*A saída real do terminal e o relatório real do exemplo fictício, reproduzidos como animação.*

![O topo de um relatório de comparação: quatro alertas e o término do projeto 21 dias depois](docs/img/pt/hero.png)

*Saída real: duas revisões da rodovia fictícia de [`examples/`](examples/LEIA-ME.md), comparadas.
Tudo nela é inventado.*

## O que ela pega

Todas as imagens de relatório deste guia são saída real do exemplo fictício, uma rodovia entregue duas
vezes, com um mês de intervalo (rev03 e rev04). O relatório sai no idioma do cronograma.

**Um registro reescrito depois do fato.** O término real da linha 29 era 05/06/2026 na rev03 e
aparece como 01/06/2026 na rev04, exatamente a data da linha de base. A linha 119, a 100%, foi
removida, e 473.600 de valor agregado foram junto. Nenhum dos dois arquivos avisa.

![Passado reescrito: um término real alterado e uma atividade com avanço removida](docs/img/pt/past-rewritten.png)

**Avanço que não é só avanço.** O número de cabeçalho andou 4,57 pontos, de 23,44% para 28,01%.
Atividade por atividade, o trabalho soma 4,90. Os 0,33 pontos de diferença não são trabalho feito,
e o relatório dá nome a cada parte.

![Avanço: anterior, atual, movimento, explicado e resíduo](docs/img/pt/progress.png)

**Um marco a um dia da data limite.** Os 7 marcos com data limite ainda terminam dentro dela, o
mais apertado com 1 dia de margem. Com o escorregamento que 80% das atividades não ultrapassaram
(7 dias), 3 deles passam da data limite. O relatório também diz onde nasce cada atraso.

![Prazo e marcos: cada marco contra a sua data limite](docs/img/pt/deadlines.png)

## Começo rápido

**1. Instale.** Um comando, para todos os agentes e para o uso sem agente.

Windows (PowerShell):

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
```

macOS / Linux (Terminal):

```
curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
```

O instalador pergunta só o que é escolha sua: se você quer a aba Cronoaudit, quando ele encontra o
MS Project, e se quer ver o exemplo agora. Responda sim ao exemplo e o relatório acima abre no seu
navegador.

![Saída do instalador: onde a skill foi instalada, os relatórios do exemplo e como usar](docs/img/pt/install.png)

*Saída real do instalador no macOS, rodado de uma cópia local deste repositório, com o exemplo
aceito. Caminhos abreviados para `~`.*

**2. Peça.** Abra o agente de sua preferência, ou o que a sua empresa permite, na pasta do
cronograma e diga o que você quer:
- *Analise o Rev04.mpp.*
- *Compare o Rev03.mpp com o Rev04.mpp e me diga o que mudou.*
- *Quais marcos correm risco de passar da data limite?*

No Windows com o MS Project, o agente recebe o `.mpp` direto. Nos outros casos, salve antes o
cronograma como XML (**Arquivo → Salvar como → Formato XML**).

**Sem agente?** Use os botões da aba Cronoaudit no Project, ou um comando sobre o XML exportado.
Veja [Escolha como usar](#escolha-como-usar). Os detalhes de cada passo, e como instalar um
agente, estão em [Instalar](#instalar).

## Por que usar

| | |
|---|---|
| **29 segundos** | para analisar um cronograma real de 6.484 tarefas e 107 calendários, num notebook comum (Apple M1, medido em 22/11/2026). |
| **Ao centavo** | o valor agregado da cronoaudit é conferido, atividade por atividade, com o que o próprio MS Project calculou. Quando não bate, o relatório diz onde. |
| **14 de 14** | problemas plantados no exemplo fictício aparecem no relatório. A lista do que foi plantado está em [`examples/`](examples/LEIA-ME.md), e um teste automático confere a cada versão. |
| **12 cobranças prontas** | na comparação entre duas revisões do exemplo, uma por evidência, a integridade da medição primeiro. |
| **Nada inventado** | os números saem do motor, não do agente. Cada afirmação vem marcada como medida, inferida ou relatada. |

## O que você recebe

Um relatório que abre no navegador, no idioma do cronograma. Cada seção começa com uma leitura
curta, escrita por regras.

**Uma revisão:** o prazo primeiro (cada marco contra a data limite, com a margem e onde nasce o
atraso); nove verificações de integridade; a curva S com os dados do próprio arquivo;
produtividade por recurso; catorze métricas de qualidade da rede; Earned Schedule e as próximas
semanas; a forense de onde entrou o atraso de cada marco.

![Relatório de uma revisão: o avanço, a leitura e as nove verificações](docs/img/pt/review-top.png)

A curva S é desenhada com os dados distribuídos no tempo do próprio arquivo, e a leitura diz o que
o outro método de valor agregado informaria:

![Curva S: previsto e realizado, IDP 0,902](docs/img/pt/s-curve.png)

**Duas revisões comparadas, na ordem em que se lê:** 1. prazo; 2. se a medição é confiável;
3. o que o plano mudou; 4. avanço; 5. folga e caminho crítico; 6. qualidade da rede; e, no fim,
**o que cobrar da contratada**. No exemplo são 12 cobranças, cada uma citando a sua linha:

<p align="center">
<img src="docs/img/pt/ask.png" alt="O que cobrar da contratada: 12 cobranças em três grupos" width="720">
</p>

## Escolha como usar

![Como funciona: o motor mede no seu computador e não envia nada. Você chega a ele conversando com um agente de IA por meio da skill, clicando num botão dentro do MS Project, ou sem IA nenhuma.](docs/img/pt/how-it-works.png)

| Você prefere | Caminho | O que você faz |
|---|---|---|
| Conversar com uma IA e deixar ela fazer tudo | **A. Pelo agente** | *"analise o Rev04.mpp"* |
| Um botão, dentro do próprio Project | **B. Pela aba Cronoaudit** | clica em **Relatório** ou **Analisar** |
| Sem IA, ou num computador sem agente | **C. Pelo motor** | um comando, sobre o XML exportado |

Nos três, o motor roda no seu computador e não envia nada. O que muda é quem conversa com você.

### A. Pelo agente

Para quem gosta de pedir e deixar fazer. No Windows com o MS Project instalado, você não precisa
exportar nada: o agente passa o `.mpp` para a cronoaudit, que pede ao próprio Project para
exportar o arquivo e segue a análise. O arquivo é aberto só para leitura e não muda. Se ele já
estiver aberto no Project, a sua janela não é tocada: a cronoaudit lê a versão salva em disco.

Exemplos do que dizer:
- *Analise o Rev04.mpp.*
- *Compare o Rev03.mpp com o Rev04.mpp e me diga o que mudou.*
- *Analise o cronograma que está aberto no Project.*
- *Quais marcos correm risco de passar da data limite?*
- *Escreva a síntese e gere o relatório final.*

Use o agente de sua preferência, ou o que a sua empresa permite no seu computador. Este guia
mostra três: Claude Code, GitHub Copilot e Codex (OpenAI). Como instalar está em
[Instalar](#instalar).

**Como é uma conversa.** Isto é um exemplo, de um teste com a rodovia fictícia em 22/11/2026. Os
números são os do motor:

> **Você:** Compare a rev03 com a rev04 e me diga o que mudou, por assunto.
>
> **Agente:** O término do projeto foi de 04/10/2027 para 25/10/2027, 21 dias depois. Antes do
> avanço, três pontos pedem resposta da contratada: o término real da linha 29 foi reescrito e
> passou a coincidir com a data da linha de base; a linha 119, a 100%, foi removida e levou o
> valor agregado junto; e a linha de base da linha 132 mudou. O atraso do marco do viaduto nasce
> na linha 148 e cresce na linha 157, cuja duração passou de 12 para 20 dias…

### B. Pela aba Cronoaudit, dentro do Project (Windows)

Para quem prefere um botão. A aba fica entre **Projeto** e **Exibir**:

| Grupo | Botão | O que faz |
|---|---|---|
| Com o agente de IA | **Analisar** | pergunta o modo (secreto ou livre) e abre o seu agente com o cronograma aberto |
| | **Comparar versões** | pergunta o modo, mostra as outras versões da mesma pasta e abre o agente com as duas |
| Sem IA | **Relatório** | gera o relatório e abre no navegador; nada sai do computador |
| | **Comparar** | o mesmo, para duas versões |
| | **Exportar XML** | só exporta, para levar a outro lugar |
| Ajustes | **Configurar** | agente, pasta dos relatórios, modo |

Os botões nunca perguntam se é para salvar o seu arquivo: eles leem a versão salva em disco.

A aba abre o Claude Code, o Codex ou o GitHub Copilot, o primeiro que encontrar no computador.
Para experimentar sem um cronograma seu, abra o `rodovia-ficticia-rev04.mpp` da pasta
`cronoaudit-exemplo`, que o instalador cria na sua pasta de usuário.

Antes de abrir o agente, Analisar e Comparar versões perguntam o modo. **Sim** é o modo secreto,
e já vem selecionado: o agente abre numa pasta só com a cópia codificada, e o relatório com os
dados reais é montado no seu computador no fim. **Não** é o modo livre, desta vez. Para não
perguntar mais, escolha o modo em **Configurar** (item 5). Veja o [modo secreto](#modo-secreto).

O instalador da cronoaudit oferece a aba quando encontra o MS Project no computador (veja
[Instalar](#instalar)). Para instalar só a aba, ou instalar de novo, com o Project fechado:

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/msproject/install-msproject.ps1 | iex
```

Durante a instalação o Project abre e pede duas coisas, que são suas:
1. se aparecer a janela de **Logon** com perfis, escolha **Computador**;
2. no aviso sobre macros do modelo, clique em **Desabilitar macros**.

O instalador guarda uma cópia do que muda antes de mudar, não altera nenhuma configuração de
segurança e confere no fim que os botões respondem. Para remover, defina
`$env:CRONOAUDIT_MSPROJECT_REMOVE="1"` na mesma janela e rode o mesmo comando. Pelo botão, o modo
secreto é uma escolha na hora de abrir o agente: o botão roda a cópia codificada e abre o agente nela.
Mais detalhes em [`msproject/`](msproject/LEIA-ME.md).

### C. Pelo motor, sem agente

Para quando não há agente no computador, ou quando a política da empresa não permite usar um.
Mesmo relatório, sem conversa, e nada sai do computador.

1. No MS Project: **Arquivo → Salvar como → Formato XML (\*.xml)**. É o formato do próprio
   Project; nada do que a cronoaudit precisa se perde.
2. No PowerShell (as duas primeiras linhas acham o Python; veja [Instalar](#instalar)):

```
$py = "$env:LOCALAPPDATA\cronoaudit\python\python.exe"
if (-not (Test-Path $py)) { $py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" } }
& $py "$env:USERPROFILE\.claude\skills\cronoaudit\scripts\review.py" "C:\caminho\do\cronograma.xml"
```

Dois arquivos, o anterior primeiro, geram a comparação. No Windows com o Project, o comando
também aceita o `.mpp` direto. Se a análise com agente for feita em outro computador, que seja um
computador autorizado pela empresa a receber o cronograma.

## Instalar

### Como abrir o PowerShell (Windows)

1. Aperte a tecla Windows.
2. Digite `PowerShell`.
3. Clique em **Windows PowerShell**.

Abre uma janela com um cursor piscando. Cole o comando com o botão direito do mouse e aperte
Enter. Use essa janela, não o "Prompt de Comando" (cmd). No macOS, abra o **Terminal**.

### 1. A cronoaudit (sempre)

Um comando instala a cronoaudit para todos os agentes e para o uso sem agente.

**Windows (PowerShell):**

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
```

**macOS / Linux (Terminal):**

```
curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
```

O instalador faz o resto e pergunta só o que é escolha sua:
- no Windows, traz o Python se o computador não tiver um, sem precisar de administrador;
- se encontrar o MS Project, pergunta se você quer também a aba Cronoaudit;
- copia o exemplo fictício para a pasta `cronoaudit-exemplo` e pergunta se você quer vê-lo agora:
  ele compara duas revisões de uma obra inventada e abre o relatório no navegador;
- no fim, mostra como usar, com o comando certo para o seu computador.

No fim aparece **`Pronto: cronoaudit 1.0.0 instalada.`** Para atualizar, rode o mesmo comando de
novo.

Para ver o exemplo de novo, use a última linha que o instalador mostrou, a que termina em
`--example`. O que foi plantado nele, e onde aparece no relatório, está em
[`examples/`](examples/LEIA-ME.md).

No Windows, o Python que o instalador traz não entra no PATH, então `python` sozinho não o
encontra. Por isso os comandos do Windows neste guia começam por duas linhas que acham o Python
certo. A linha que o instalador mostra no fim também serve.

### 2. Um agente (só para o caminho A, ou para o botão Analisar)

Escolha um. Comandos oficiais de cada fornecedor, em novembro de 2026. Depois de instalar, feche o
PowerShell e abra outro. Cada agente precisa de uma conta no fornecedor; confira qual plano o
inclui e a política da sua empresa.

| Agente | Windows (PowerShell) | Abrir | Guia oficial |
|---|---|---|---|
| Claude Code (Anthropic) | `irm https://claude.ai/install.ps1 \| iex` | `claude` | [code.claude.com](https://code.claude.com/docs/en/setup) |
| GitHub Copilot CLI | `winget install GitHub.Copilot` | `copilot` | [docs.github.com](https://docs.github.com/pt/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli) |
| Codex (OpenAI) | `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 \| iex"` | `codex` | [github.com/openai/codex](https://github.com/openai/codex) |

No macOS e no Linux, os guias oficiais trazem o comando de cada um. No Copilot, se ele vem da
empresa, é a empresa que decide se a CLI está habilitada.

Os três leem a pasta de skills que o instalador da cronoaudit criou. Para conferir, abra o
agente e pergunte *"quais skills você tem?"*. A cronoaudit foi testada de ponta a ponta com o
Claude Code e, no modo livre, com o GitHub Copilot CLI (21/11/2026, pela aba do Project). No
Codex, a instalação segue o que o fornecedor documenta. O modo secreto foi testado com o
Claude Code e, em 25/11/2026, com o GitHub Copilot CLI: sem a trava, que só existe no Claude
Code, ele seguiu as regras escritas da pasta, falou só por códigos, não rodou o motor e pediu
antes de escrever a síntese.

### 3. A aba no Project (só para o caminho B)

O instalador do passo 1 oferece a aba quando encontra o MS Project. Os detalhes estão no
[caminho B](#b-pela-aba-cronoaudit-dentro-do-project-windows).

## Para onde vão os seus dados

- **O motor roda no seu computador e não envia nada.** Ele não usa a rede.
- **Os instaladores baixam** este repositório do GitHub e, no Windows e só se precisar, o Python do
  python.org. Mais nada.
- **O agente é outra história.** O que ele lê (o cronograma, o relatório, as suas perguntas) vai
  para o fornecedor dele, nos termos da sua conta ou da conta da empresa. Confira a política da
  empresa antes de usar um agente com cronograma de contrato.
- **Se a política não permite agente,** use o caminho C, ou os botões "Sem IA" da aba.

### Modo secreto

Para conversar com o agente sem que os nomes, os valores e as datas saiam do seu computador. Pela
aba do Project, responda **Sim** quando Analisar ou Comparar perguntarem o modo. Sem a aba, você
mesmo roda um comando, com o `.xml` ou, no Windows com o Project, com o `.mpp`:

```
$py = "$env:LOCALAPPDATA\cronoaudit\python\python.exe"
if (-not (Test-Path $py)) { $py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" } }
& $py "$env:USERPROFILE\.claude\skills\cronoaudit\scripts\review.py" "C:\caminho\do\Rev04.mpp" --secret
```

A cronoaudit analisa o arquivo real no seu computador e grava uma cópia codificada numa pasta
separada: nomes viram códigos como `T·3fa91c`, datas viram contagens como `D+0412`, e os valores
são multiplicados por um fator secreto. Durações, percentuais e números de linha continuam reais.
Você abre o agente nessa pasta, e ele lê só a cópia. Quando você pede o relatório final, a
cronoaudit decodifica no seu computador e abre com os nomes reais.

Para ler uma resposta do agente com os nomes reais, rode no seu PowerShell, fora do agente, o
comando que o próprio agente indica (`secret_decode.py text` com o caminho da pasta), cole a
resposta e termine com Ctrl+Z e Enter numa linha sozinha.

O que ele faz e o que não faz:
- No Claude Code, a pasta traz regras e uma trava que mantêm o agente dentro dela. Só as
  ferramentas de que a sessão precisa ficam abertas; PowerShell, conectores (OneDrive, SharePoint,
  Microsoft 365), envio de arquivos e mensagens para outras sessões ficam fechados. Os outros
  agentes recebem as mesmas regras como instruções escritas.
- Os códigos não tornam o cronograma anônimo: a estrutura e as durações continuam legíveis.
- Não substitui a política da sua empresa sobre serviços de IA.

Testado no Windows com o Claude Code em 22 e 23/11/2026, pelo comando, direto do `.mpp` e pelo
botão do Project, e num cronograma real de 6.484 tarefas: nenhum nome, data ou valor real chegou à
cópia codificada, e a trava foi conferida chamando-a direto, sem o agente.

## Se algo der errado

| O que aparece | O que fazer |
|---|---|
| *'irm' não é reconhecido* | Você está no Prompt de Comando (cmd). Abra o PowerShell. |
| *python não é reconhecido* | O Python que o instalador traz não entra no PATH. Use a linha que o instalador mostrou no fim, ou comece pelas duas linhas que acham o Python, como nos comandos deste guia. |
| O comando do agente não é encontrado | Feche o PowerShell e abra outro. |
| O agente não conhece a cronoaudit | Feche o agente e abra de novo. No Copilot, `/skills reload`. Pergunte *"quais skills você tem?"*. |
| `/cronoaudit` não faz nada | Comandos com `/` só funcionam dentro do agente, não no PowerShell. Pode só pedir com palavras. |
| *O MS Project não foi encontrado* | O `.mpp` só é lido por um computador com o Project. Use o caminho C com o XML exportado por quem tem o Project. |
| Aviso de *alterações não salvas* | É informativo: o Project marca o arquivo assim só por abrir. A análise leu a versão salva em disco. |
| A aba não aparece | Feche e abra o Project. Se continuar, rode o instalador da aba de novo. |
| No modo secreto, o Claude Code pergunta se você confia na pasta | Responda que sim. Sem isso, a trava da pasta fica desligada. A pergunta volta a cada análise, porque cada uma tem a sua pasta. |
| O modo secreto diz que foi iniciado por um agente | Rode o comando num PowerShell aberto pelo menu Iniciar, ou abra o Project pelo menu Iniciar, não de dentro do terminal de um agente. |

## Mais

- **Como funciona por dentro.** O motor lê o XML que o próprio Project exporta (MSPDI), que traz
  tarefas, vínculos, as onze linhas de base, calendários e campos personalizados. Quando você passa
  um `.mpp`, a cronoaudit pede ao Project instalado para fazer essa exportação. O processo completo,
  em inglês: [`skills/cronoaudit/references/usage.md`](skills/cronoaudit/references/usage.md).
- **Guia ilustrado**, 23 páginas: a revisão 4 da rodovia fictícia contada do começo ao fim, com o
  terminal, o relatório, o modo secreto lado a lado e uma folha de consulta.
  [Português](docs/guia/guia-pt.pdf), [inglês](docs/guia/guia-en.pdf).
- **Manual**, dezessete capítulos, da versão 1.0: [português](docs/manual/manual-pt.pdf),
  [inglês](docs/manual/manual-en.pdf). Conceitos, instalação, os três caminhos, a aba do Project,
  os modos livre e secreto, o relatório seção por seção e como reproduzir cada número.
- **O exemplo fictício**, para experimentar primeiro: [`examples/`](examples/LEIA-ME.md). Os
  números deste guia saem dos `.xml` do exemplo; os `.mpp` dão um pouco diferente (+22 dias, 14
  cobranças), porque o Project recalculou o cronograma ao criá-los.

### Outras formas de instalar

| Caminho | Comando |
|---|---|
| Qualquer cliente de Agent Skills | `npx skills add Holiv/cronoaudit -g` |
| Claude Code, como plugin | `/plugin marketplace add Holiv/cronoaudit`, depois `/plugin install cronoaudit@cronoaudit` |
| Codex | `$skill-installer https://github.com/Holiv/cronoaudit` |
| Uma equipe, pelo projeto | `git clone https://github.com/Holiv/cronoaudit .agents/skills/cronoaudit` dentro do projeto |

Opções do instalador no Windows, definidas na mesma janela antes do comando:
`$env:CRONOAUDIT_NO_PYTHON="1"` (nunca baixar Python), `$env:CRONOAUDIT_EMBED_PYTHON="1"` (usar o
Python próprio mesmo havendo outro), `$env:CRONOAUDIT_REF="nome-da-branch"` (outra branch).

### O que ela não faz

Não lê Primavera P6. Não produz pleito contratual de atraso: a forense mostra o mecanismo, e um
pleito precisa de registros contemporâneos e de um método formal. Não certifica DCMA: as catorze
métricas são uma implementação, identificada como tal.

### Conferir a ferramenta

`python skills/cronoaudit/scripts/test_checks.py`, a partir de uma cópia deste repositório.

### Procedência

Escrita a partir de um método documentado e genérico, sem portar o código de nenhuma aplicação, e
medida num programa real de 6.484 tarefas com 107 calendários. Números de escala ficam;
identidades saem: nenhum empregador, contratada, contrato, quilometragem, pessoa ou valor aparece
neste repositório.

### Licença

Apache 2.0. © 2026 Helton da Silva de Oliveira.
