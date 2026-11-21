# cronoaudit dentro do MS Project

A cronoaudit é uma **skill**: o agente (Claude Code, Codex, GitHub Copilot, Gemini CLI) lê o
cronograma por ela, conversa com você, interpreta e personaliza o relatório quando você pede. O
motor em Python é o instrumento da skill: é dele que saem os números, para o agente nunca
inventar um.

O suplemento é só o **atalho de entrada**. Ele exporta o XML do arquivo aberto e abre um terminal
com a skill já iniciada sobre ele. Tudo o que ele faz você pode fazer à mão (seção 7).

**Estado: v0.2.1, beta.** A v0.2 foi usada de ponta a ponta em duas máquinas Windows: com o
GitHub Copilot CLI numa e o Claude Code na outra, os dois agentes relataram os mesmos números do
motor. Novo na v0.2.1 e ainda não medido em máquina real: a rota pelo VS Code, a lista de
arquivos no `pedido.md` e a tela de configuração.

## 1. Os botões

| Botão (macro) | O que faz | O dado sai da máquina? |
|---|---|---|
| **Analisar** (`CronoauditAnalisar`) | exporta o XML, grava o `pedido.md` e abre o agente na pasta, já com a skill iniciada | **sim**: o que o agente ler (o XML, os resultados, a conversa) vai para o provedor do agente |
| **Comparar** (`CronoauditComparar`) | pede a outra versão (.mpp ou .xml), exporta as duas e abre o agente com o pedido de comparação | **sim**, idem |
| **Exportar XML** (`CronoauditExportarXml`) | só exporta o XML e abre a pasta no Explorer | **não**. Nada é enviado e nada roda. O que você fizer com o XML depois é com você |
| **Sem IA** (`CronoauditSemIA`) | exporta, roda o motor da cronoaudit e abre o relatório HTML | **não**. Tudo roda nesta máquina |
| **Comparar sem IA** (`CronoauditCompararSemIA`) | o mesmo, para a comparação de duas versões | **não** |
| **Configurar** (`CronoauditConfigurar`) | mostra a configuração atual e deixa trocar agente, pasta, Python, `review.py`, o aviso de dados, ou redefinir tudo | não |

Sobre o "sim": o suplemento não envia nada. Quem envia é o agente, ao provedor dele, nas condições
da sua conta ou da conta da empresa. Na primeira vez que você usa Analisar ou Comparar aparece um
aviso dizendo isso, com a opção de não mostrar de novo. **Se a política da empresa não permite
IA, use os dois botões "sem IA"**: o relatório é o mesmo, só não há conversa.

Se Analisar ou Comparar não encontrarem nenhum agente instalado, eles oferecem rodar sem IA em
vez de falhar.

### O que acontece no Analisar

1. Confere o arquivo: está aberto, salvo em disco, sem alteração pendente (oferece salvar), e
   avisa se for um mestre com subprojetos.
2. Cria a pasta da rodada e exporta o XML para ela.
3. Grava `pedido.md` (UTF-8) na pasta: a tarefa, o nome do XML, o idioma (pt-BR), o comando do
   motor que já funciona nesta máquina, a regra de que todo número vem do motor, e **o nome exato
   de cada arquivo que o motor vai gravar** (relatório, JSON e leituras), para o agente não
   adivinhar.
4. Abre um terminal **visível** nessa pasta, com o agente iniciado numa frase curta em ASCII:
   `Use the cronoaudit skill. Read pedido.md in this folder and follow it.` O pedido de verdade
   está no arquivo; a frase curta evita problema de acento na linha de comando.

O terminal fica aberto. A conversa segue ali: peça o que quiser aprofundar, ou peça para
personalizar o relatório.

### O agente

| Agente | Comando que o suplemento usa |
|---|---|
| Claude Code | `claude "…"` |
| Codex CLI | `codex "…"` |
| GitHub Copilot CLI | `copilot -i "…"` |
| Gemini CLI | `gemini -i "…"` |
| VS Code (Copilot Chat) | `code "<pasta da rodada>"`, com o pedido na área de transferência |

Por padrão o suplemento abre o primeiro que encontrar no PATH, nessa ordem. Para fixar um, use
`CronoauditConfigurar`, item 1.

O VS Code é o último da lista porque não recebe o pedido pela linha de comando. O suplemento abre
a pasta da rodada nele e copia a frase curta: abra o Copilot Chat (`Ctrl+Alt+I`), escolha o modo
**Agente** e cole com `Ctrl+V`. Se o Copilot Chat do VS Code lê a skill instalada em
`~/.agents/skills` ainda não foi medido; se ele disser que não conhece a skill, peça que leia o
`SKILL.md` em `%USERPROFILE%\.agents\skills\cronoaudit`.

## 2. Pré-requisitos

- Windows com MS Project (desktop).
- A cronoaudit instalada pelo `install.ps1` (ver o README principal). O instalador traz um Python
  próprio quando a máquina não tem um. O suplemento procura o `review.py` em
  `%USERPROFILE%\.claude\skills\cronoaudit` e `%USERPROFILE%\.agents\skills\cronoaudit`, e o
  Python nesta ordem: `py -3`, `python`, `python3`, `%LOCALAPPDATA%\cronoaudit\python\python.exe`.
- Para Analisar e Comparar: um dos quatro agentes instalado e com login feito. Sem agente, os
  botões "sem IA" e o Exportar XML funcionam do mesmo jeito.

## 3. Teste de viabilidade (5 minutos, uma vez por máquina)

Mede o que decide se o suplemento funciona nesta máquina: se o Project grava XML por macro, qual
documento fica ativo depois, se a macro consegue executar um processo e se acha o Python.

1. Abra um cronograma **salvo** no Project. De preferência uma cópia.
2. `Alt+F11` abre o editor do VBA. No painel da esquerda, clique em `ProjectGlobal (Global.MPT)`,
   **não** no `VBAProject` do seu arquivo. Importar dentro do arquivo deixa o cronograma com
   alteração não salva, o teste recusa rodar, e quem salva grava a macro dentro do cronograma.
3. `Arquivo > Importar arquivo...` e escolha `CronoauditTeste.bas`.
4. Feche o editor. `Alt+F8`, escolha `CronoauditTeste`, `Executar`.
5. O Bloco de Notas abre com o resultado (`%TEMP%\cronoaudit-teste\resultado.txt`).
6. Remova o módulo de teste: `Alt+F11`, botão direito em `modCronoauditTeste` (dentro de
   `ProjectGlobal`) > `Remover`, sem exportar. Se o Project perguntar ao fechar se salva o
   Global, pode salvar: o módulo já saiu.

Como ler o resultado:

| Linha | Bom | Ruim, e o que significa |
|---|---|---|
| `[1] XML gravado` | SIM | NÃO: a máquina bloqueia gravação por macro. O suplemento não serve aqui; use o terminal (seção 7). |
| `documento ativo depois` | qualquer um, desde que `ativo agora` volte ao original | o original não reabriu: anote o erro |
| `[2] cmd` | código de saída 0 | BLOQUEADO: a política (ASR) impede a macro de abrir processos. Só o Exportar XML funciona |
| `[3] Python` | alguma linha com código 0 e versão ≥ 3.9 | todas ≠ 0: rode o `install.ps1` de novo, ele traz o Python |

## 4. Instalação do suplemento

As macros moram no `Global.MPT`, que guarda as macros pessoais de cada um. Por isso o suplemento
**nunca substitui o Global**: importa um módulo dentro dele.

1. Feche todos os cronogramas e abra o Project vazio.
2. `Alt+F11`. No painel da esquerda, selecione `ProjectGlobal (Global.MPT)`.
3. Se já existir um módulo `Cronoaudit` (a v0.1, por exemplo), remova antes (botão direito >
   Remover, sem exportar). Senão o novo nasce como `Cronoaudit1` e as macros ficam duplicadas.
4. `Arquivo > Importar arquivo...` e escolha `Cronoaudit.bas`.
5. `Depurar > Compilar ProjectGlobal`. Não pode aparecer erro.
6. Com `ProjectGlobal` selecionado, `Ctrl+S`. Ao fechar o Project, aceite salvar o Global.

Se aparecer um erro do VBA durante o uso, **não clique em "Fim"** com uma janela da macro
aberta: isso pode fechar o Project. Use "Depurar" ou feche a mensagem.

## 5. Botões na faixa de opções

1. `Arquivo > Opções > Personalizar Faixa de Opções`.
2. `Nova Guia`, renomeie para `cronoaudit`. Dentro dela, `Novo Grupo`, renomeie para `Skill`.
3. Em "Escolher comandos em", selecione `Macros`. Adicione ao grupo, nesta ordem, as cinco
   macros de trabalho: `CronoauditAnalisar`, `CronoauditComparar`, `CronoauditExportarXml`,
   `CronoauditSemIA`, `CronoauditCompararSemIA`. `CronoauditConfigurar` pode ir num segundo grupo.
4. Renomeie cada um (Analisar, Comparar, Exportar XML, Sem IA, Comparar sem IA) e escolha um
   ícone.

Quem tinha botões da v0.1: `CronoauditAuditar` e `CronoauditConversar` não existem mais. Remova
esses botões e aponte os novos para as macros acima. Sem a faixa, tudo funciona por `Alt+F8`.

## 6. Onde ficam os arquivos

Em `%LOCALAPPDATA%\cronoaudit\relatorios\<data>_<arquivo>\`, uma pasta por rodada, com o XML, o
`pedido.md` e, depois que o motor rodar, o relatório HTML e os JSON. **A pasta é local de
propósito**: fica fora do OneDrive, porque o XML e o relatório carregam o dado da obra. Troque em
`CronoauditConfigurar`, item 2.

No nome da pasta e do XML, os caracteres que atrapalham caminho ou linha de comando viram `_`, e
o nome é cortado em 60 caracteres.

## 7. A rota só pelo terminal continua valendo

O suplemento não é necessário. À mão:

1. No Project: `Arquivo > Salvar como > Formato XML`.
2. Abra um terminal na pasta do XML e inicie o seu agente (`claude`, `codex`, `copilot`,
   `gemini`).
3. Peça: *use a skill cronoaudit e analise este cronograma*.

Sem agente: `python "%USERPROFILE%\.claude\skills\cronoaudit\scripts\review.py" arquivo.xml`.
Para comparar, passe os dois XML, o anterior primeiro.

## 8. Como a comparação se comporta

Comparar pergunta se o arquivo aberto é a versão mais nova e abre a janela para escolher a
outra. Um `.mpp` é aberto só para leitura, exportado e fechado sem salvar; um `.xml` é copiado.
As tarefas são casadas pelo UID e depois pelo nome e caminho da EAP. O "Salvar como" troca o
GUID, não o UID. A outra versão não pode estar aberta no Project.

## 9. Problemas conhecidos e o que fazer

| Sintoma | Causa provável | Saída |
|---|---|---|
| no VS Code, nada acontece depois de abrir | o pedido não é enviado sozinho | abra o Copilot Chat em modo Agente e cole (`Ctrl+V`) |
| "Não encontrei nenhum agente no PATH" | agente não instalado, ou instalado com o Project aberto (o Project herda o PATH ao abrir) | feche e abra o Project; ou aceite rodar sem IA |
| o terminal abre e o agente reclama da opção `-i` | versão antiga do Copilot CLI ou do Gemini CLI | atualize o agente; ou digite o nome dele no terminal e cole a frase que o terminal mostra |
| o agente abre mas diz que não conhece a skill | skill não instalada para esse agente | rode o `install.ps1`; no agente, peça para listar as skills |
| o agente pede para confiar na pasta ou para rodar um comando | comportamento normal do agente | confirme: a pasta é a da rodada e o comando é o do `pedido.md` |
| "Não consegui gravar o XML" | política da máquina bloqueia gravação por macro | `Salvar como > XML` e terminal (seção 7) |
| "abrir o agente" ou "executar o Python" falhou | regra ASR que impede o Office de abrir processos | use Exportar XML e abra o terminal à mão |
| "Não achei Python" | Python ausente ou só o atalho da Microsoft Store | rode o `install.ps1` de novo; ou `CronoauditConfigurar`, item 3 |
| "Não achei a skill cronoaudit" | skill não instalada | `install.ps1`; ou `CronoauditConfigurar`, item 4 |
| a janela de escolher arquivo não abre | `Shell.Application` bloqueado | o suplemento pede o caminho por digitação |
| "Salve em disco" com o arquivo salvo | arquivo aberto do OneDrive/SharePoint pelo navegador ou Recentes, o Project devolve uma URL | abra pela pasta sincronizada; o teste mostra isso na linha `[0]` |
| o original voltou sem o desfazer | quando o "Salvar como" troca o documento ativo, o original é reaberto do disco | esperado; nas máquinas medidas o ativo continuou sendo o `.mpp` |
| o aviso de dados não aparece mais e você quer rever | foi marcado para não mostrar | `CronoauditConfigurar`, item 5 |
| `Cronoaudit1` na lista de módulos, macros em dobro | a versão anterior não foi removida antes de importar | remova os dois módulos e importe de novo |
