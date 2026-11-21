Attribute VB_Name = "Cronoaudit"
' cronoaudit para MS Project - v0.2 (21/11/2026)
'
' A cronoaudit e uma SKILL: o agente le o cronograma por ela, conversa com o planejador,
' interpreta e personaliza o relatorio. O motor em Python e o instrumento da skill: e dele
' que saem os numeros, para o agente nunca inventar um. Este modulo e so o atalho de entrada:
' exporta o XML e abre um terminal com a skill ja iniciada sobre ele.
'
' Macros publicas, da mais usada para a menos:
'   CronoauditAnalisar        exporta o XML do arquivo ativo, grava pedido.md na pasta da rodada
'                             e abre o agente (Claude Code, Codex, Copilot CLI, Gemini CLI) nela.
'                             O que o agente ler vai para o provedor dele.
'   CronoauditComparar        pede a outra versao (.mpp ou .xml), exporta as duas e abre o agente
'                             com o pedido de comparacao. Idem quanto ao dado.
'   CronoauditExportarXml     so exporta o XML e abre a pasta. Sem agente, sem motor.
'   CronoauditSemIA           exporta, roda o motor e abre o relatorio. Nada sai da maquina.
'   CronoauditCompararSemIA   o mesmo para a comparacao de versoes. Nada sai da maquina.
'   CronoauditConfigurar      agente, pasta dos relatorios, Python, review.py, redefinir.
'
' Precisa de Python 3.9+ e da skill instalada pelo install.ps1 da cronoaudit.
' Configuracao em HKCU\Software\VB and VBA Program Settings\cronoaudit\config
'   agente    auto | claude | codex | copilot | gemini      pasta   onde as rodadas sao gravadas
'   python    comando do Python (ex.: py -3)                review  caminho do review.py
'   aviso_ia  1 = nao mostrar de novo o aviso de dados      ultimo  pasta da ultima rodada
'   outro     ultima "outra versao" escolhida no Comparar
'
' Este arquivo e ASCII puro (subconjunto do cp1252) com fim de linha CRLF: o editor do VBA
' importa no codigo de pagina da maquina. Por isso as mensagens nao levam acento.
' O pedido.md e gravado em UTF-8; o texto passado na linha de comando e ASCII e curto.

Option Explicit

Private Const APP As String = "cronoaudit"
Private Const SEC As String = "config"
Private Const TITULO As String = "cronoaudit"
Private Const AGENTES As String = "claude codex copilot gemini"
' Curto e ASCII de proposito: e a unica frase que atravessa a linha de comando.
Private Const PROMPT_INICIAL As String = "Use the cronoaudit skill. Read pedido.md in this folder and follow it."

' ===================== macros publicas =====================

Public Sub CronoauditAnalisar()
    FluxoAnalise True
End Sub

Public Sub CronoauditComparar()
    FluxoComparacao True
End Sub

Public Sub CronoauditExportarXml()
    Dim origem As String, pasta As String, base As String, destino As String
    If Not PreVoo(origem) Then Exit Sub
    base = NomeBase(ActiveProject.Name)
    pasta = NovaPastaDeRodada(base)
    If pasta = "" Then Exit Sub
    destino = pasta & "\" & base & ".xml"
    If Not ExportarXml(destino, origem, True) Then Exit Sub
    SaveSetting APP, SEC, "ultimo", pasta
    MsgBox "XML exportado em:" & vbCrLf & destino & vbCrLf & vbCrLf & _
        "A pasta vai abrir. Para analisar, abra o seu agente nessa pasta e peca:" & vbCrLf & _
        "  use a skill cronoaudit e leia este XML" & vbCrLf & vbCrLf & _
        "Nada foi enviado a lugar nenhum e o motor nao rodou.", vbInformation, TITULO
    On Error Resume Next
    Shell "explorer.exe /select,""" & destino & """", vbNormalFocus
    On Error GoTo 0
End Sub

Public Sub CronoauditSemIA()
    FluxoAnalise False
End Sub

Public Sub CronoauditCompararSemIA()
    FluxoComparacao False
End Sub

Public Sub CronoauditConfigurar()
    Dim op As String, v As String
    op = InputBox("Configuracao atual:" & vbCrLf & _
        "  1  agente: " & GetSetting(APP, SEC, "agente", "auto") & vbCrLf & _
        "  2  pasta: " & PastaRaiz() & vbCrLf & _
        "  3  Python: " & ValorOuAuto(GetSetting(APP, SEC, "python", "")) & vbCrLf & _
        "  4  review.py: " & ValorOuAuto(GetSetting(APP, SEC, "review", "")) & vbCrLf & _
        "  5  mostrar de novo o aviso de dados" & vbCrLf & _
        "  9  redefinir tudo" & vbCrLf & vbCrLf & _
        "Digite o numero do que quer mudar:", TITULO, "1")
    If StrPtr(op) = 0 Then Exit Sub
    Select Case Trim$(op)
        Case "1"
            v = InputBox("Agente que o Analisar e o Comparar abrem:" & vbCrLf & vbCrLf & _
                "  auto     o primeiro que existir, nesta ordem: claude, codex, copilot, gemini" & vbCrLf & _
                "  claude   Claude Code" & vbCrLf & _
                "  codex    Codex CLI" & vbCrLf & _
                "  copilot  GitHub Copilot CLI" & vbCrLf & _
                "  gemini   Gemini CLI", TITULO, GetSetting(APP, SEC, "agente", "auto"))
            If StrPtr(v) = 0 Then Exit Sub
            v = LCase$(Trim$(v))
            If v = "" Then v = "auto"
            If v <> "auto" And Not EhAgente(v) Then
                MsgBox "Agente desconhecido: " & v & vbCrLf & "Use auto, claude, codex, copilot ou gemini.", vbExclamation, TITULO
                Exit Sub
            End If
            SaveSetting APP, SEC, "agente", v
            If v <> "auto" Then
                If Not NoPath(v) Then
                    MsgBox "Guardado, mas o comando '" & v & "' nao foi encontrado no PATH agora." & vbCrLf & _
                        "Se acabou de instalar, feche e abra o Project.", vbExclamation, TITULO
                End If
            End If
        Case "2"
            v = InputBox("Pasta onde as rodadas sao gravadas (vazio = voltar ao padrao):" & vbCrLf & vbCrLf & _
                "O padrao e local, fora de pasta sincronizada, porque o XML e o relatorio carregam o dado da obra.", _
                TITULO, PastaRaiz())
            If StrPtr(v) = 0 Then Exit Sub
            v = Trim$(v)
            Do While Len(v) > 3 And Right$(v, 1) = "\"
                v = Left$(v, Len(v) - 1)
            Loop
            If v = "" Then DeleteSettingSeguro "pasta" Else SaveSetting APP, SEC, "pasta", v
        Case "3"
            v = InputBox("Comando do Python (vazio = detectar de novo):", TITULO, GetSetting(APP, SEC, "python", ""))
            If StrPtr(v) = 0 Then Exit Sub
            If Trim$(v) = "" Then DeleteSettingSeguro "python" Else SaveSetting APP, SEC, "python", Trim$(v)
        Case "4"
            v = InputBox("Caminho do review.py (vazio = detectar de novo):", TITULO, GetSetting(APP, SEC, "review", ""))
            If StrPtr(v) = 0 Then Exit Sub
            If Trim$(v) = "" Then DeleteSettingSeguro "review" Else SaveSetting APP, SEC, "review", Trim$(v)
        Case "5"
            DeleteSettingSeguro "aviso_ia"
            MsgBox "O aviso de dados volta a aparecer no proximo Analisar ou Comparar.", vbInformation, TITULO
        Case "9"
            If MsgBox("Apagar toda a configuracao da cronoaudit neste usuario?" & vbCrLf & vbCrLf & _
                "Os relatorios ja gravados nao sao apagados.", vbOKCancel + vbExclamation, TITULO) = vbOK Then
                On Error Resume Next
                DeleteSetting APP, SEC
                On Error GoTo 0
                MsgBox "Configuracao redefinida.", vbInformation, TITULO
            End If
        Case Else
            MsgBox "Opcao desconhecida: " & op, vbExclamation, TITULO
    End Select
End Sub

' ===================== fluxos =====================

' comIA = True: pedido.md + agente. comIA = False: motor + relatorio, tudo local.
' Sem agente disponivel, o fluxo com IA oferece o outro em vez de falhar.
Private Sub FluxoAnalise(ByVal comIA As Boolean)
    Dim origem As String, pasta As String, base As String, xmlAtual As String
    Dim py As String, rv As String, agente As String
    If Not PreVoo(origem) Then Exit Sub
    If Not AcharMotor(py, rv) Then Exit Sub
    If comIA Then
        If Not ResolverAgente(agente, comIA) Then Exit Sub
    End If
    base = NomeBase(ActiveProject.Name)
    pasta = NovaPastaDeRodada(base)
    If pasta = "" Then Exit Sub
    xmlAtual = pasta & "\" & base & ".xml"
    If Not ExportarXml(xmlAtual, origem, True) Then Exit Sub
    SaveSetting APP, SEC, "ultimo", pasta
    If comIA Then
        If Not GravarUtf8(pasta & "\pedido.md", PedidoAnalise(base & ".xml", pasta, py, rv)) Then Exit Sub
        AbrirAgente agente, pasta
    Else
        If RodarMotor(py, rv, """" & xmlAtual & """", pasta) Then
            AbrirRelatorio pasta & "\" & base & "-review.html"
        End If
    End If
End Sub

Private Sub FluxoComparacao(ByVal comIA As Boolean)
    Dim origem As String, outro As String, pasta As String, py As String, rv As String
    Dim xmlAtivo As String, xmlOutro As String, ativoEhAtual As VbMsgBoxResult
    Dim baseAtivo As String, baseOutro As String, agente As String
    Dim anterior As String, atual As String, baseAnt As String, baseAtu As String
    If Not PreVoo(origem) Then Exit Sub
    If Not AcharMotor(py, rv) Then Exit Sub
    If comIA Then
        If Not ResolverAgente(agente, comIA) Then Exit Sub
    End If

    ativoEhAtual = MsgBox("O arquivo aberto e a versao MAIS NOVA?" & vbCrLf & vbCrLf & _
        "Sim: em seguida escolha a versao anterior." & vbCrLf & _
        "Nao: em seguida escolha a versao mais nova.", vbYesNoCancel + vbQuestion, TITULO)
    If ativoEhAtual = vbCancel Then Exit Sub

    outro = EscolherArquivo()
    If outro = "" Then Exit Sub
    If LCase$(outro) = LCase$(origem) Then
        MsgBox "Voce escolheu o proprio arquivo aberto. Escolha a outra versao.", vbExclamation, TITULO
        Exit Sub
    End If

    If AtivarSeAberto(outro) Then
        AtivarSeAberto origem
        MsgBox "A outra versao esta aberta no Project. Feche-a antes de comparar.", vbExclamation, TITULO
        Exit Sub
    End If

    baseAtivo = NomeBase(ActiveProject.Name)
    baseOutro = NomeBase(Mid$(outro, InStrRev(outro, "\") + 1))
    If LCase$(baseOutro) = LCase$(baseAtivo) Then baseOutro = baseOutro & "-outra"
    pasta = NovaPastaDeRodada(baseAtivo)
    If pasta = "" Then Exit Sub
    xmlAtivo = pasta & "\" & baseAtivo & ".xml"
    xmlOutro = pasta & "\" & baseOutro & ".xml"
    If Not ExportarXml(xmlAtivo, origem, True) Then Exit Sub

    If LCase$(Right$(outro, 4)) = ".xml" Then
        On Error Resume Next
        FileCopy outro, xmlOutro
        If Err.Number <> 0 Then
            Falha "copiar " & outro, Err
            On Error GoTo 0
            Exit Sub
        End If
        On Error GoTo 0
    Else
        If Not ExportarOutro(outro, xmlOutro, origem) Then Exit Sub
    End If

    If ativoEhAtual = vbYes Then
        anterior = xmlOutro: atual = xmlAtivo: baseAnt = baseOutro: baseAtu = baseAtivo
    Else
        anterior = xmlAtivo: atual = xmlOutro: baseAnt = baseAtivo: baseAtu = baseOutro
    End If
    SaveSetting APP, SEC, "ultimo", pasta
    If comIA Then
        If Not GravarUtf8(pasta & "\pedido.md", PedidoComparacao(baseAnt & ".xml", baseAtu & ".xml", pasta, py, rv)) Then Exit Sub
        AbrirAgente agente, pasta
    Else
        If RodarMotor(py, rv, """" & anterior & """ """ & atual & """", pasta) Then
            AbrirRelatorio pasta & "\" & baseAnt & "--to--" & baseAtu & "-cycle.html"
        End If
    End If
End Sub

' ===================== agente =====================

' Decide qual agente abrir. Devolve False para desistir. Quando nao ha agente e a pessoa
' aceita a rota sem IA, devolve True com comIA = False.
Private Function ResolverAgente(ByRef agente As String, ByRef comIA As Boolean) As Boolean
    Dim cfg As String, motivo As String
    cfg = LCase$(Trim$(GetSetting(APP, SEC, "agente", "auto")))
    If cfg = "" Or Not (cfg = "auto" Or EhAgente(cfg)) Then cfg = "auto"
    If cfg = "auto" Then
        agente = AcharAgente()
        motivo = "Nao encontrei nenhum agente no PATH (claude, codex, copilot, gemini)."
    Else
        If NoPath(cfg) Then agente = cfg Else agente = ""
        motivo = "O agente configurado ('" & cfg & "') nao foi encontrado no PATH."
    End If
    If agente = "" Then
        If MsgBox(motivo & vbCrLf & _
            "Se acabou de instalar um, feche e abra o Project." & vbCrLf & vbCrLf & _
            "Rodar agora SEM IA? O motor da cronoaudit gera o relatorio nesta maquina, " & _
            "sem conversa e sem enviar nada." & vbCrLf & vbCrLf & _
            "Sim: rodar sem IA.    Nao: cancelar.", vbYesNo + vbQuestion, TITULO) = vbYes Then
            comIA = False
            ResolverAgente = True
        End If
        Exit Function
    End If
    ResolverAgente = AvisoDeDados(agente)
End Function

' Aviso unico: com o agente no centro, o dado sai da maquina. Nao e confirmacao a cada clique.
Private Function AvisoDeDados(ByVal agente As String) As Boolean
    If GetSetting(APP, SEC, "aviso_ia", "") = "1" Then
        AvisoDeDados = True
        Exit Function
    End If
    Select Case MsgBox("Este botao abre o agente '" & agente & "' sobre o cronograma exportado." & vbCrLf & vbCrLf & _
        "O que o agente ler (o XML, os resultados, o que voce escrever) e enviado ao provedor dele, " & _
        "nas condicoes da sua conta ou da sua empresa. Confira se a politica da empresa permite." & vbCrLf & vbCrLf & _
        "Se nao permitir, use CronoauditSemIA e CronoauditCompararSemIA: o relatorio e gerado " & _
        "nesta maquina e nada sai dela." & vbCrLf & vbCrLf & _
        "Sim: continuar e nao mostrar este aviso de novo." & vbCrLf & _
        "Nao: continuar e mostrar de novo na proxima vez." & vbCrLf & _
        "Cancelar: nao abrir o agente.", vbYesNoCancel + vbInformation, TITULO)
        Case vbYes
            SaveSetting APP, SEC, "aviso_ia", "1"
            AvisoDeDados = True
        Case vbNo
            AvisoDeDados = True
    End Select
End Function

' Abre um terminal visivel na pasta da rodada, com o agente iniciado sobre o pedido curto.
' cmd /k mantem a janela. Formas de chamada, cada uma conferida na documentacao do proprio CLI:
'   claude "PROMPT"        sessao interativa com pedido inicial
'   codex "PROMPT"         idem
'   copilot -i "PROMPT"    --interactive: sessao interativa que executa o pedido
'   gemini -i "PROMPT"     --prompt-interactive: executa o pedido e continua interativo
Private Function AbrirAgente(ByVal agente As String, ByVal pasta As String) As Boolean
    Dim sh As Object, linha As String, cmd As String
    Select Case agente
        Case "claude", "codex"
            linha = agente & " """ & PROMPT_INICIAL & """"
        Case "copilot", "gemini"
            linha = agente & " -i """ & PROMPT_INICIAL & """"
        Case Else
            MsgBox "Agente desconhecido: " & agente, vbCritical, TITULO
            Exit Function
    End Select
    ' Aspas externas: o cmd retira a primeira e a ultima e executa o miolo como esta.
    ' Os textos do echo nao podem conter ( ) & | < > ^ % !
    cmd = "cmd /k ""title cronoaudit && cd /d """ & pasta & """ && " & linha & _
        " || (echo. & echo O agente terminou com erro ou nao chegou a abrir. & " & _
        "echo Para tentar de novo, abra o agente nesta pasta e digite: & " & _
        "echo   " & PROMPT_INICIAL & ")"""
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then
        Falha "abrir o terminal (WScript.Shell bloqueado)", Err
        On Error GoTo 0
        Exit Function
    End If
    sh.Run cmd, 1, False
    If Err.Number <> 0 Then
        Falha "abrir o agente (a politica da maquina pode bloquear processos abertos por macro)", Err
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    AbrirAgente = True
End Function

Private Function AcharAgente() As String
    Dim c As Variant
    For Each c In Split(AGENTES, " ")
        If NoPath(CStr(c)) Then
            AcharAgente = CStr(c)
            Exit Function
        End If
    Next c
End Function

Private Function EhAgente(ByVal nome As String) As Boolean
    If nome = "" Or InStr(nome, " ") > 0 Then Exit Function
    EhAgente = (InStr(" " & AGENTES & " ", " " & nome & " ") > 0)
End Function

' Verdadeiro se o comando existe no PATH que o Project herdou ao abrir.
' So aceita nome simples: o valor vai para uma linha de comando.
Private Function NoPath(ByVal comando As String) As Boolean
    Dim sh As Object, rc As Long
    If Not EhAgente(comando) Then Exit Function
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    rc = sh.Run("cmd /c where " & comando & " >nul 2>&1", 0, True)
    If Err.Number = 0 Then NoPath = (rc = 0)
    Err.Clear
    On Error GoTo 0
End Function

' ===================== pedido.md =====================

Private Function PedidoCabecalho(ByVal tarefa As String) As String
    PedidoCabecalho = "# Pedido para a skill cronoaudit" & vbCrLf & vbCrLf & _
        "Gerado pelo suplemento da cronoaudit para MS Project em " & Format(Now, "dd/mm/yyyy hh:nn") & "." & vbCrLf & vbCrLf & _
        "- Tarefa: " & tarefa & vbCrLf & _
        "- Idioma: portugues do Brasil (pt-BR). Converse e escreva em pt-BR, com acentuacao normal." & vbCrLf
End Function

Private Function PedidoRegras(ByVal linhaDeComando As String, ByVal py As String, ByVal rv As String) As String
    PedidoRegras = vbCrLf & "## Como fazer" & vbCrLf & vbCrLf & _
        "1. Use a skill **cronoaudit**. Leia o SKILL.md dela antes de qualquer coisa e siga o que ele diz." & vbCrLf & _
        "2. Rode o motor da skill uma unica vez, gravando nesta pasta. O comando que ja funciona nesta maquina:" & vbCrLf & vbCrLf & _
        "   ```" & vbCrLf & _
        "   " & linhaDeComando & vbCrLf & _
        "   ```" & vbCrLf & vbCrLf & _
        "   Python: `" & py & "`  |  review.py: `" & rv & "`" & vbCrLf & _
        "   (no PowerShell, um executavel entre aspas precisa de `&` na frente)" & vbCrLf & _
        "3. **Todo numero vem do motor.** Leia os arquivos JSON que ele grava e cite as leituras prontas " & _
        "(`-readings.json`). Nao calcule, nao estime e nao arredonde por conta propria. Se um numero nao " & _
        "estiver nos arquivos, diga que nao esta." & vbCrLf & _
        "4. Diga o caminho completo do relatorio HTML gerado e resuma o que merece atencao, comecando " & _
        "pelos avisos que bloqueiam. Depois pergunte o que a pessoa quer aprofundar." & vbCrLf & _
        "5. Nao altere os XML. Nao rode a analise de novo sem que pecam ou sem que o arquivo mude." & vbCrLf & _
        "6. Personalizacao do relatorio ou do padrao da empresa: so quando pedirem, pelo fluxo que o SKILL.md descreve." & vbCrLf
End Function

Private Function PedidoAnalise(ByVal xmlNome As String, ByVal pasta As String, ByVal py As String, ByVal rv As String) As String
    PedidoAnalise = PedidoCabecalho("analise critica do cronograma") & _
        "- Arquivo: `" & xmlNome & "` (nesta pasta; exportacao XML do MS Project, MSPDI)" & vbCrLf & _
        PedidoRegras(py & " """ & rv & """ """ & pasta & "\" & xmlNome & """ --outdir """ & pasta & """ --lang pt", py, rv)
End Function

Private Function PedidoComparacao(ByVal xmlAnterior As String, ByVal xmlAtual As String, ByVal pasta As String, _
                                  ByVal py As String, ByVal rv As String) As String
    PedidoComparacao = PedidoCabecalho("comparacao de duas versoes do mesmo cronograma (relatorio de ciclo)") & _
        "- Versao ANTERIOR: `" & xmlAnterior & "` (nesta pasta)" & vbCrLf & _
        "- Versao ATUAL: `" & xmlAtual & "` (nesta pasta)" & vbCrLf & _
        "- A ordem importa: no comando, a anterior vem primeiro. O motor gera a analise critica da " & _
        "versao atual e o relatorio de ciclo entre as duas." & vbCrLf & _
        PedidoRegras(py & " """ & rv & """ """ & pasta & "\" & xmlAnterior & """ """ & pasta & "\" & xmlAtual & _
            """ --outdir """ & pasta & """ --lang pt", py, rv)
End Function

' Grava texto em UTF-8 sem BOM, sem depender de ADODB. Trata pares substitutos.
Private Function GravarUtf8(ByVal caminho As String, ByVal txt As String) As Boolean
    Dim b() As Byte, n As Long, i As Long, c As Long, c2 As Long, f As Integer
    If Len(txt) = 0 Then Exit Function
    ReDim b(0 To Len(txt) * 3 + 3)
    i = 1
    Do While i <= Len(txt)
        c = AscW(Mid$(txt, i, 1)) And &HFFFF&
        If c >= &HD800& And c <= &HDBFF& And i < Len(txt) Then
            c2 = AscW(Mid$(txt, i + 1, 1)) And &HFFFF&
            If c2 >= &HDC00& And c2 <= &HDFFF& Then
                c = &H10000 + (c - &HD800&) * &H400& + (c2 - &HDC00&)
                i = i + 1
            End If
        End If
        If c >= &HD800& And c <= &HDFFF& Then c = 63   ' substituto solto: "?"
        If c < &H80& Then
            b(n) = c: n = n + 1
        ElseIf c < &H800& Then
            b(n) = &HC0 Or (c \ &H40&)
            b(n + 1) = &H80 Or (c And &H3F)
            n = n + 2
        ElseIf c < &H10000 Then
            b(n) = &HE0 Or (c \ &H1000&)
            b(n + 1) = &H80 Or ((c \ &H40&) And &H3F)
            b(n + 2) = &H80 Or (c And &H3F)
            n = n + 3
        Else
            b(n) = &HF0 Or (c \ &H40000)
            b(n + 1) = &H80 Or ((c \ &H1000&) And &H3F)
            b(n + 2) = &H80 Or ((c \ &H40&) And &H3F)
            b(n + 3) = &H80 Or (c And &H3F)
            n = n + 4
        End If
        i = i + 1
    Loop
    ReDim Preserve b(0 To n - 1)
    On Error Resume Next
    If ArquivoExiste(caminho) Then Kill caminho
    Err.Clear
    f = FreeFile
    Open caminho For Binary Access Write As #f
    If Err.Number = 0 Then Put #f, , b
    If Err.Number <> 0 Then
        Falha "gravar " & caminho, Err
        Close #f
        On Error GoTo 0
        Exit Function
    End If
    Close #f
    On Error GoTo 0
    GravarUtf8 = True
End Function

' ===================== etapas =====================

' Bloqueia antes de exportar: ha arquivo, esta em disco, sem alteracoes pendentes.
' Alteracoes pendentes importam porque o "Salvar como" pode trocar o documento ativo e o
' original e reaberto do disco: sem salvar, a alteracao se perderia.
Private Function PreVoo(ByRef origem As String) As Boolean
    Dim i As Long
    If Projects.Count = 0 Then
        MsgBox "Abra um cronograma primeiro.", vbExclamation, TITULO
        Exit Function
    End If
    origem = ActiveProject.FullName
    If InStr(origem, "\") = 0 Then
        MsgBox "Salve o cronograma em disco antes de continuar.", vbExclamation, TITULO
        Exit Function
    End If
    If LCase$(Right$(origem, 4)) = ".xml" Then
        MsgBox "O arquivo aberto ja e um XML. Abra o .mpp, ou use a cronoaudit direto pelo terminal sobre este XML.", vbExclamation, TITULO
        Exit Function
    End If
    If Not ActiveProject.Saved Then
        If MsgBox("O cronograma tem alteracoes nao salvas." & vbCrLf & vbCrLf & _
            "Sim: salvar agora e continuar." & vbCrLf & "Nao: cancelar.", vbYesNo + vbExclamation, TITULO) <> vbYes Then Exit Function
        On Error Resume Next
        FileSave
        If Err.Number <> 0 Then
            Falha "salvar o cronograma", Err
            On Error GoTo 0
            Exit Function
        End If
        On Error GoTo 0
        If Not ActiveProject.Saved Then
            MsgBox "O cronograma nao foi salvo. Cancelado.", vbExclamation, TITULO
            Exit Function
        End If
        origem = ActiveProject.FullName
    End If
    For i = 1 To Projects.Count
        If Not Projects(i).Saved Then
            MsgBox "Ha outro cronograma aberto com alteracoes nao salvas:" & vbCrLf & Projects(i).FullName & vbCrLf & vbCrLf & _
                "Salve ou feche antes de continuar: a exportacao pode fechar e reabrir arquivos.", vbExclamation, TITULO
            Exit Function
        End If
    Next i
    If ActiveProject.Subprojects.Count > 0 Then
        If MsgBox("Este arquivo e um mestre com " & ActiveProject.Subprojects.Count & _
            " subprojetos. A analise de um mestre e menos confiavel que a de cada subprojeto. Continuar?", _
            vbOKCancel + vbExclamation, TITULO) <> vbOK Then Exit Function
    End If
    PreVoo = True
End Function

' Grava o projeto ativo em XML (MSPDI). Se o "Salvar como" trocar o documento ativo para o
' XML, fecha o XML sem salvar e, se reabrir = True, reabre o original pelo caminho.
' Application.Alerts volta a True em todos os caminhos.
Private Function ExportarXml(ByVal destino As String, ByVal original As String, ByVal reabrir As Boolean) As Boolean
    Dim errNum As Long, errDesc As String
    On Error Resume Next
    If ArquivoExiste(destino) Then Kill destino
    Err.Clear
    Application.Alerts False
    FileSaveAs Name:=destino, FormatID:="MSProject.XML"
    errNum = Err.Number: errDesc = Err.Description
    Err.Clear
    Application.Alerts True
    On Error GoTo 0

    If LCase$(ActiveProject.FullName) <> LCase$(original) Then
        On Error Resume Next
        FileCloseEx Save:=pjDoNotSave
        If Err.Number <> 0 Then Err.Clear: DoEvents: FileClose Save:=pjDoNotSave
        Err.Clear
        If AtivarSeAberto(destino) Then
            MsgBox "O XML ficou aberto no Project e nao consegui fechar. Feche sem salvar:" & vbCrLf & destino, vbExclamation, TITULO
        End If
        If reabrir Then
            If Not AtivarSeAberto(original) Then FileOpenEx Name:=original
            If Err.Number <> 0 Then
                MsgBox "O XML foi gerado, mas nao consegui reabrir o original:" & vbCrLf & original & vbCrLf & _
                    "Erro " & Err.Number & ": " & Err.Description & vbCrLf & "Abra o arquivo manualmente.", vbCritical, TITULO
                Err.Clear
            End If
        End If
        On Error GoTo 0
    End If

    If errNum <> 0 Or Not ArquivoExiste(destino) Then
        MsgBox "Nao consegui gravar o XML em:" & vbCrLf & destino & vbCrLf & vbCrLf & _
            "Erro " & errNum & ": " & errDesc & vbCrLf & vbCrLf & _
            "Se a politica da maquina bloqueia gravacao por macro, use Arquivo > Salvar como > XML e abra a skill pelo terminal.", _
            vbCritical, TITULO
        Exit Function
    End If
    If FileLen(destino) = 0 Then
        MsgBox "O XML foi criado vazio: " & destino, vbCritical, TITULO
        Exit Function
    End If
    ExportarXml = True
End Function

' Abre o outro cronograma so para leitura, exporta, fecha sem salvar e devolve o foco ao original.
Private Function ExportarOutro(ByVal caminho As String, ByVal destino As String, ByVal original As String) As Boolean
    Dim ok As Boolean
    Application.Alerts False
    On Error Resume Next
    FileOpenEx Name:=caminho, ReadOnly:=True, openPool:=pjDoNotOpenPool
    If Err.Number <> 0 Then
        Application.Alerts True
        Falha "abrir " & caminho, Err
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    Application.Alerts True
    If LCase$(ActiveProject.FullName) <> LCase$(caminho) Then
        MsgBox "Abri o arquivo, mas o ativo nao e ele:" & vbCrLf & ActiveProject.FullName & vbCrLf & "Nada foi exportado.", vbCritical, TITULO
        Exit Function
    End If
    ok = ExportarXml(destino, caminho, False)
    If LCase$(ActiveProject.FullName) = LCase$(caminho) Then
        On Error Resume Next
        FileCloseEx Save:=pjDoNotSave
        If Err.Number <> 0 Then Err.Clear: DoEvents: FileClose Save:=pjDoNotSave
        Err.Clear
        On Error GoTo 0
    End If
    If AtivarSeAberto(caminho) Then
        MsgBox "A outra versao ficou aberta (somente leitura). Feche sem salvar:" & vbCrLf & caminho, vbExclamation, TITULO
    End If
    If Not AtivarSeAberto(original) Then
        On Error Resume Next
        FileOpenEx Name:=original
        If Err.Number <> 0 Then
            MsgBox "Nao consegui reabrir o original:" & vbCrLf & original & vbCrLf & "Abra o arquivo manualmente.", vbCritical, TITULO
            Err.Clear
        End If
        On Error GoTo 0
    End If
    ExportarOutro = ok
End Function

' Roda o review.py numa janela de terminal visivel e espera. Em erro, a janela fica aberta.
Private Function RodarMotor(ByVal py As String, ByVal rv As String, ByVal arquivos As String, ByVal pasta As String) As Boolean
    Dim sh As Object, cmd As String, rc As Long
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then
        Falha "abrir o terminal (WScript.Shell bloqueado)", Err
        On Error GoTo 0
        Exit Function
    End If
    cmd = py & " """ & rv & """ " & arquivos & " --outdir """ & pasta & """"
    rc = sh.Run("cmd /c ""title cronoaudit && " & cmd & " || (echo. & echo A cronoaudit terminou com erro. & pause & exit /b 1)""", 1, True)
    If Err.Number <> 0 Then
        Falha "executar o Python (a politica da maquina pode bloquear processos abertos por macro)", Err
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If rc <> 0 Then
        MsgBox "A cronoaudit terminou com codigo " & rc & ". A mensagem dela ficou no terminal." & vbCrLf & vbCrLf & _
            "Comando:" & vbCrLf & cmd, vbExclamation, TITULO
        Exit Function
    End If
    RodarMotor = True
End Function

Private Sub AbrirRelatorio(ByVal html As String)
    On Error Resume Next
    If Not ArquivoExiste(html) Then
        MsgBox "A cronoaudit rodou, mas o relatorio esperado nao esta em:" & vbCrLf & html, vbExclamation, TITULO
        Shell "explorer.exe """ & Left$(html, InStrRev(html, "\") - 1) & """", vbNormalFocus
    Else
        Shell "explorer.exe """ & html & """", vbNormalFocus
    End If
    On Error GoTo 0
End Sub

' ===================== descoberta =====================

Private Function AcharMotor(ByRef py As String, ByRef rv As String) As Boolean
    Dim c As Variant
    rv = GetSetting(APP, SEC, "review", "")
    If Not ArquivoExiste(rv) Then rv = ""
    If rv = "" Then
        For Each c In Array(Environ$("USERPROFILE") & "\.claude\skills\cronoaudit\scripts\review.py", _
                            Environ$("USERPROFILE") & "\.agents\skills\cronoaudit\scripts\review.py")
            If ArquivoExiste(CStr(c)) Then
                rv = CStr(c)
                Exit For
            End If
        Next c
        If rv = "" Then
            MsgBox "Nao achei a skill cronoaudit instalada (review.py)." & vbCrLf & vbCrLf & _
                "Instale com o comando do README, ou informe o caminho em CronoauditConfigurar.", vbCritical, TITULO
            Exit Function
        End If
        SaveSetting APP, SEC, "review", rv
    End If

    py = GetSetting(APP, SEC, "python", "")
    If py <> "" Then
        If PythonServe(py) Then
            AcharMotor = True
            Exit Function
        End If
    End If
    For Each c In Array("py -3", "python", "python3", """" & Environ$("LOCALAPPDATA") & "\cronoaudit\python\python.exe""")
        If PythonServe(CStr(c)) Then
            py = CStr(c)
            SaveSetting APP, SEC, "python", py
            AcharMotor = True
            Exit Function
        End If
    Next c
    MsgBox "Nao achei Python 3.9 ou mais novo que a macro consiga executar." & vbCrLf & vbCrLf & _
        "Rode de novo o instalador da cronoaudit (ele traz um Python proprio), ou informe o comando em CronoauditConfigurar.", vbCritical, TITULO
End Function

' Verdadeiro se o comando executa um Python >= 3.9. O alias da Microsoft Store devolve 9009.
Private Function PythonServe(ByVal py As String) As Boolean
    Dim sh As Object, rc As Long
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number = 0 Then
        rc = sh.Run("cmd /c """ & py & " -c ""import sys; sys.exit(0 if sys.version_info >= (3, 9) else 3)""""", 0, True)
        If Err.Number = 0 Then PythonServe = (rc = 0)
    End If
    Err.Clear
    On Error GoTo 0
End Function

' Janela do Windows para escolher arquivo (BrowseForFolder com arquivos visiveis).
' O Project nao expoe FileDialog de forma confiavel. Se a janela falhar, cai para InputBox.
Private Function EscolherArquivo() As String
    Dim shApp As Object, item As Object, p As String, falhou As Boolean
    On Error Resume Next
    Set shApp = CreateObject("Shell.Application")
    Set item = shApp.BrowseForFolder(0, "Escolha a outra versao do cronograma (.mpp ou .xml)", &H4000 + &H10 + &H40, 0)
    falhou = (Err.Number <> 0)
    If Not falhou And Not item Is Nothing Then p = item.Self.Path
    falhou = falhou Or (Err.Number <> 0)
    Err.Clear
    On Error GoTo 0
    If Not falhou And p = "" Then Exit Function   ' cancelou a janela
    If falhou Then
        p = InputBox("Caminho completo da outra versao (.mpp ou .xml):", TITULO, GetSetting(APP, SEC, "outro", ""))
    End If
    If p = "" Then Exit Function
    If InStrRev(p, ".") <= InStrRev(p, "\") Then
        MsgBox "Escolha um .mpp ou um .xml.", vbExclamation, TITULO
        Exit Function
    End If
    If Not ArquivoExiste(p) Then
        MsgBox "Arquivo nao encontrado:" & vbCrLf & p, vbExclamation, TITULO
        Exit Function
    End If
    Select Case LCase$(Mid$(p, InStrRev(p, ".")))
        Case ".mpp", ".xml"
        Case Else
            MsgBox "Escolha um .mpp ou um .xml.", vbExclamation, TITULO
            Exit Function
    End Select
    SaveSetting APP, SEC, "outro", p
    EscolherArquivo = p
End Function

' ===================== utilitarios =====================

Private Function AtivarSeAberto(ByVal caminho As String) As Boolean
    Dim i As Long
    For i = 1 To Projects.Count
        If LCase$(Projects(i).FullName) = LCase$(caminho) Then
            Projects(i).Activate
            AtivarSeAberto = True
            Exit Function
        End If
    Next i
End Function

' Dir levanta erro em caminho invalido (unidade inexistente, caractere proibido): aqui vira Falso.
Private Function ArquivoExiste(ByVal caminho As String) As Boolean
    If Len(caminho) = 0 Then Exit Function
    On Error Resume Next
    ArquivoExiste = (Dir(caminho, vbNormal) <> "")
    If Err.Number <> 0 Then ArquivoExiste = False
    Err.Clear
    On Error GoTo 0
End Function

Private Function ValorOuAuto(ByVal v As String) As String
    If v = "" Then ValorOuAuto = "(detectar)" Else ValorOuAuto = v
End Function

' Pasta local por padrao (%LOCALAPPDATA%), fora do OneDrive: o XML e o relatorio tem dado da obra.
Private Function PastaRaiz() As String
    PastaRaiz = GetSetting(APP, SEC, "pasta", Environ$("LOCALAPPDATA") & "\cronoaudit\relatorios")
End Function

' Cria e devolve a pasta da rodada, ou "" (com mensagem) se nao conseguir.
Private Function NovaPastaDeRodada(ByVal base As String) As String
    Dim raiz As String, p As String, existe As Boolean
    raiz = PastaRaiz()
    CriarPastas raiz
    p = raiz & "\" & Format(Now, "yyyy-mm-dd_hhnnss") & "_" & base
    CriarPastas p
    On Error Resume Next
    existe = False
    existe = (Dir(p, vbDirectory) <> "")
    Err.Clear
    On Error GoTo 0
    If Not existe Then
        MsgBox "Nao consegui criar a pasta da rodada:" & vbCrLf & p & vbCrLf & vbCrLf & _
            "Troque a pasta em CronoauditConfigurar.", vbCritical, TITULO
        Exit Function
    End If
    NovaPastaDeRodada = p
End Function

Private Sub CriarPastas(ByVal p As String)
    Dim partes() As String, i As Long, acc As String
    If Right$(p, 1) = "\" Then p = Left$(p, Len(p) - 1)
    If p = "" Then Exit Sub
    partes = Split(p, "\")
    acc = partes(0)
    On Error Resume Next
    For i = 1 To UBound(partes)
        acc = acc & "\" & partes(i)
        If partes(i) <> "" Then
            If Dir(acc, vbDirectory) = "" Then MkDir acc
            Err.Clear   ' raiz de caminho de rede (\\servidor\compart) nao responde ao Dir
        End If
    Next i
    On Error GoTo 0
End Sub

' Nome sem extensao, seguro para caminho e para linha de comando do cmd.
' Project.Name pode vir com ou sem ".mpp" (extensoes ocultas no Windows).
' Troca por "_": os proibidos em nome de arquivo, os que o cmd interpreta mesmo entre aspas
' (% ! ^ &), caracteres de controle e tudo fora do Latin-1 (Dir, MkDir e Open do VBA usam a
' API ANSI: um caractere fora do codigo de pagina viraria "?" e o caminho deixaria de existir).
' Limita o tamanho por causa do limite de 260 do caminho, e nao termina em ponto ou espaco.
Private Function NomeBase(ByVal nome As String) As String
    Dim i As Long, ch As String, r As String, cod As Long
    If InStrRev(nome, ".") > 0 Then
        Select Case LCase$(Mid$(nome, InStrRev(nome, ".")))
            Case ".mpp", ".xml", ".mpt": nome = Left$(nome, InStrRev(nome, ".") - 1)
        End Select
    End If
    For i = 1 To Len(nome)
        ch = Mid$(nome, i, 1)
        cod = AscW(ch) And &HFFFF&
        If cod < 32 Or cod > 255 Or (cod >= 127 And cod <= 160) Then
            r = r & "_"
        ElseIf InStr("\/:*?""<>|&^%!", ch) > 0 Then
            r = r & "_"
        Else
            r = r & ch
        End If
    Next i
    r = Trim$(r)
    If Len(r) > 60 Then r = Trim$(Left$(r, 60))
    Do While Len(r) > 0 And (Right$(r, 1) = "." Or Right$(r, 1) = " ")
        r = Left$(r, Len(r) - 1)
    Loop
    If r = "" Then r = "cronograma"
    NomeBase = r
End Function

Private Sub DeleteSettingSeguro(ByVal chave As String)
    On Error Resume Next
    DeleteSetting APP, SEC, chave
    On Error GoTo 0
End Sub

Private Sub Falha(ByVal etapa As String, ByVal e As ErrObject)
    MsgBox "Falhou ao " & etapa & "." & vbCrLf & vbCrLf & _
        "Erro " & e.Number & " (" & e.Source & "): " & e.Description, vbCritical, TITULO
    e.Clear
End Sub
