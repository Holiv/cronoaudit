# cronoaudit dentro do MS Project

Três botões no Project, sobre o arquivo aberto:

| Botão (macro) | O que faz | O dado sai da máquina? |
|---|---|---|
| **Auditar** (`CronoauditAuditar`) | exporta o XML, roda a cronoaudit, abre o relatório | não |
| **Comparar** (`CronoauditComparar`) | pede a outra versão (.mpp ou .xml), exporta por trás, roda a comparação | não |
| **Conversar** (`CronoauditConversar`) | abre o agente (Claude Code, Copilot, Codex, Gemini) na pasta da última auditoria | sim, o que o agente ler |

A rota pelo terminal continua valendo: `Arquivo > Salvar como > XML` e
`python review.py arquivo.xml`. O plugin só tira esses passos da frente.

**Estado: v0.1, não testado em máquina real.** Rode primeiro o teste de viabilidade (passo 2).

## 1. Pré-requisitos

- Windows com MS Project (desktop).
- Python 3.9 ou mais novo.
- A cronoaudit instalada (`install.ps1`, ver o README principal). O plugin procura o `review.py`
  em `%USERPROFILE%\.claude\skills\cronoaudit` e `%USERPROFILE%\.agents\skills\cronoaudit`.

## 2. Teste de viabilidade (5 minutos, antes de tudo)

Mede o que decide se o plugin funciona nesta máquina: se o Project grava XML por macro, qual
documento fica ativo depois, se a macro consegue executar um processo e se acha o Python.

1. Abra um cronograma **salvo** no Project.
2. `Alt+F11` abre o editor do VBA. No painel da esquerda, clique em `VBAProject (<seu arquivo>)`.
3. `Arquivo > Importar arquivo...` e escolha `CronoauditTeste.bas`.
4. Feche o editor. `Alt+F8`, escolha `CronoauditTeste`, `Executar`.
5. O Bloco de Notas abre com o resultado (`%TEMP%\cronoaudit-teste\resultado.txt`).
6. Feche o cronograma **sem salvar**, para o módulo de teste não ficar no arquivo.

Como ler o resultado:

| Linha | Bom | Ruim, e o que significa |
|---|---|---|
| `[1] XML gravado` | SIM | NÃO: a máquina bloqueia gravação por macro. O plugin não serve aqui; use o terminal. |
| `documento ativo depois` | qualquer um, desde que `ativo agora` volte ao original | o original não reabriu: anote o erro |
| `[2] cmd` | código de saída 0 | BLOQUEADO: a política (ASR) impede a macro de abrir processos |
| `[3] Python` | alguma linha com código 0 e versão ≥ 3.9 | todas ≠ 0: instale o Python, ou só a exportação funciona |

Mande o `resultado.txt` de volta: é ele que decide a arquitetura.

## 3. Instalação do plugin

As macros moram no `Global.MPT`, que guarda as macros pessoais de cada um. Por isso o plugin
**nunca substitui o Global**: importa um módulo dentro dele.

1. Feche todos os cronogramas e abra o Project vazio.
2. `Alt+F11`. No painel da esquerda, selecione `ProjectGlobal (Global.MPT)`.
3. Se já existir um módulo `Cronoaudit`, remova antes (botão direito > Remover, sem exportar).
   Senão o novo nasce como `Cronoaudit1`.
4. `Arquivo > Importar arquivo...` e escolha `Cronoaudit.bas`.
5. `Depurar > Compilar ProjectGlobal`. Não pode aparecer erro.
6. Com `ProjectGlobal` selecionado, `Ctrl+S`. Ao fechar o Project, aceite salvar o Global.

Se aparecer um erro do VBA durante o uso, **não clique em "Fim"** com uma janela da macro
aberta: isso pode fechar o Project. Use "Depurar" ou feche a mensagem.

## 4. Botões na faixa de opções

1. `Arquivo > Opções > Personalizar Faixa de Opções`.
2. `Nova Guia`, renomeie para `cronoaudit`. Dentro dela, `Novo Grupo`, renomeie para `Auditoria`.
3. Em "Escolher comandos em", selecione `Macros`. Adicione ao grupo:
   `CronoauditAuditar`, `CronoauditComparar`, `CronoauditConversar`, `CronoauditConfigurar`.
4. Renomeie cada um (Auditar, Comparar, Conversar, Configurar) e escolha um ícone.

## 5. Onde ficam os relatórios

Em `%LOCALAPPDATA%\cronoaudit\relatorios\<data>_<arquivo>\`, uma pasta por rodada, com o XML,
o relatório HTML e os JSON. **A pasta é local de propósito**: fica fora do OneDrive, porque o
XML e o relatório carregam o dado da obra. Troque em `CronoauditConfigurar`.

## 6. Como cada botão se comporta

- **Antes de exportar**, o plugin confere: há arquivo aberto, ele está salvo em disco, não tem
  alteração pendente (oferece salvar), e avisa se for um mestre com subprojetos. Alteração
  pendente importa porque o "Salvar como" pode trocar o documento ativo, e o original é reaberto
  do disco.
- **Comparar** pergunta se o arquivo aberto é a versão mais nova e abre a janela para escolher a
  outra. Um `.mpp` é aberto só para leitura, exportado e fechado sem salvar. As tarefas são
  casadas pelo UID e depois pelo nome e caminho da EAP. O "Salvar como" troca o GUID, não o UID.
- **Conversar** avisa que, a partir dali, o agente envia ao provedor dele o que ler, copia para a
  área de transferência um pedido inicial e abre o agente que encontrar no PATH. Claude Code e
  Codex já recebem o pedido; Copilot e Gemini abrem e você cola com `Ctrl+V`; sem agente de
  linha de comando, abre o VS Code na pasta para usar o Copilot de lá.

## 7. Problemas conhecidos e o que fazer

| Sintoma | Causa provável | Saída |
|---|---|---|
| "Não consegui gravar o XML" | política da máquina bloqueia gravação por macro | `Salvar como > XML` e terminal |
| "executar o Python" falhou | regra ASR que impede o Office de abrir processos | terminal |
| "Não achei Python" | Python ausente ou só o atalho da Microsoft Store | instalar Python, ou `CronoauditConfigurar` |
| "Não achei a cronoaudit" | skill não instalada | `install.ps1` |
| a janela de escolher arquivo não abre | `Shell.Application` bloqueado | o plugin pede o caminho por digitação |
| "Salve em disco" com o arquivo salvo | arquivo aberto do OneDrive/SharePoint pelo navegador ou Recentes, o Project devolve uma URL | abra pela pasta sincronizada; o teste mostra isso na linha `[0]` |
| o original voltou sem o desfazer e na exibição padrão | o "Salvar como" troca o documento ativo e o original é reaberto do disco | comportamento esperado da v0.1 |
