Attribute VB_Name = "Cronoaudit"
' cronoaudit para MS Project - v0.3 (21/11/2026)
'
' A cronoaudit e uma SKILL: o agente le o cronograma por ela, conversa com o planejador,
' interpreta e personaliza o relatorio. O motor em Python e o instrumento da skill: e dele
' que saem os numeros, para o agente nunca inventar um. Este modulo e so o atalho de entrada:
' exporta o XML e abre um terminal com a skill ja iniciada sobre ele.
'
' Macros publicas, da mais usada para a menos:
'   CronoauditAnalisar        exporta o XML do arquivo ativo, grava pedido.md na pasta da rodada
'                             e abre o agente nela: Claude Code, Codex, Copilot CLI ou Gemini CLI
'                             num terminal; ou o VS Code, com o pedido na area de transferencia.
'                             O que o agente ler vai para o provedor dele (modo LIVRE).
'                             Antes de abrir o agente, a macro confere o modo configurado.
'   CronoauditComparar        pede a outra versao (.mpp ou .xml), exporta as duas e abre o agente
'                             com o pedido de comparacao. Idem quanto ao dado.
'   CronoauditExportarXml     so exporta o XML e abre a pasta. Sem agente, sem motor.
'   CronoauditSemIA           exporta, roda o motor e abre o relatorio. Nada sai da maquina.
'   CronoauditCompararSemIA   o mesmo para a comparacao de versoes. Nada sai da maquina.
'   CronoauditConfigurar      agente, pasta dos relatorios, Python, review.py, modo, redefinir.
'
' Precisa de Python 3.9+ e da skill instalada pelo install.ps1 da cronoaudit.
' Configuracao em HKCU\Software\VB and VBA Program Settings\cronoaudit\config
'   agente    auto | claude | codex | copilot | gemini | code   pasta   onde as rodadas sao gravadas
'   python    comando do Python (ex.: py -3)                review  caminho do review.py
'   ultimo    pasta da ultima rodada                        outro   ultima "outra versao" do Comparar
'
' O MODO (livre ou secreto) nao fica no registro. Fica no arquivo que o motor e a skill tambem
' leem, para os tres concordarem:  %USERPROFILE%\.cronoaudit\config.json
'   "secret": "ask"   perguntar antes de abrir o agente (padrao de fabrica)
'   "secret": "off"   modo livre, sem perguntar
'   "secret": "on"    modo secreto por padrao. Ele ainda esta em desenvolvimento: a macro avisa
'                     e so abre o agente no modo livre se a pessoa escolher isso na hora.
' A pergunta daqui e feita por codigo, antes de o agente existir. A da skill e o agente seguindo
' instrucao. Sao coisas diferentes e o LEIA-ME diz isso.
'
' Este arquivo e ASCII puro (subconjunto do cp1252) com fim de linha CRLF: o editor do VBA
' importa no codigo de pagina da maquina. Por isso as mensagens nao levam acento.
' O pedido.md e gravado em UTF-8; o texto passado na linha de comando e ASCII e curto.

Option Explicit

Private Const APP As String = "cronoaudit"
Private Const SEC As String = "config"
Private Const TITULO As String = "cronoaudit"
' Ordem da deteccao automatica. O VS Code fica por ultimo: nao recebe o pedido pela linha de
' comando, entao depende de colar.
Private Const AGENTES As String = "claude codex copilot gemini code"
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
    Dim op As String, v As String, aviso As String
    ' O estado vai num MsgBox, que cresce com o texto. O InputBox corta o que nao cabe,
    ' entao fica so com o menu, curto. Caminhos longos aparecem com %LOCALAPPDATA% e
    ' %USERPROFILE% no lugar do comeco, cada um na sua linha.
    If MsgBox("Configuracao atual" & vbCrLf & vbCrLf & _
        "1  Agente:" & vbCrLf & "     " & GetSetting(APP, SEC, "agente", "auto") & vbCrLf & _
        "2  Pasta das rodadas:" & vbCrLf & "     " & Abreviar(PastaRaiz()) & vbCrLf & _
        "3  Python:" & vbCrLf & "     " & Abreviar(ValorOuAuto(GetSetting(APP, SEC, "python", ""))) & vbCrLf & _
        "4  review.py:" & vbCrLf & "     " & Abreviar(ValorOuAuto(GetSetting(APP, SEC, "review", ""))) & vbCrLf & _
        "5  Modo:" & vbCrLf & "     " & DescreverModo(LerSecret(aviso)) & vbCrLf & vbCrLf & _
        "OK para alterar um item. Cancelar para sair.", vbOKCancel + vbInformation, TITULO) <> vbOK Then Exit Sub
    op = InputBox("Numero do item a alterar:" & vbCrLf & vbCrLf & _
        "1 agente    2 pasta    3 Python" & vbCrLf & _
        "4 review.py    5 modo" & vbCrLf & _
        "9 redefinir tudo", TITULO, "1")
    If StrPtr(op) = 0 Then Exit Sub
    Select Case Trim$(op)
        Case "1"
            v = InputBox("auto, claude, codex, copilot," & vbCrLf & _
                "gemini ou code (VS Code)." & vbCrLf & vbCrLf & _
                "auto = o primeiro instalado," & vbCrLf & _
                "nessa ordem.", TITULO, GetSetting(APP, SEC, "agente", "auto"))
            If StrPtr(v) = 0 Then Exit Sub
            v = LCase$(Trim$(v))
            If v = "" Then v = "auto"
            If v <> "auto" And Not EhAgente(v) Then
                MsgBox "Agente desconhecido: " & v & vbCrLf & "Use auto, claude, codex, copilot, gemini ou code.", vbExclamation, TITULO
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
            v = InputBox("Pasta das rodadas." & vbCrLf & "Vazio = voltar ao padrao" & vbCrLf & _
                "(local, fora de pasta sincronizada).", TITULO, PastaRaiz())
            If StrPtr(v) = 0 Then Exit Sub
            v = Trim$(v)
            Do While Len(v) > 3 And Right$(v, 1) = "\"
                v = Left$(v, Len(v) - 1)
            Loop
            If v = "" Then DeleteSettingSeguro "pasta" Else SaveSetting APP, SEC, "pasta", v
        Case "3"
            v = InputBox("Comando do Python." & vbCrLf & "Vazio = detectar de novo.", TITULO, GetSetting(APP, SEC, "python", ""))
            If StrPtr(v) = 0 Then Exit Sub
            If Trim$(v) = "" Then DeleteSettingSeguro "python" Else SaveSetting APP, SEC, "python", Trim$(v)
        Case "4"
            v = InputBox("Caminho do review.py." & vbCrLf & "Vazio = detectar de novo.", TITULO, GetSetting(APP, SEC, "review", ""))
            If StrPtr(v) = 0 Then Exit Sub
            If Trim$(v) = "" Then DeleteSettingSeguro "review" Else SaveSetting APP, SEC, "review", Trim$(v)
        Case "5"
            v = InputBox("ask, off ou on." & vbCrLf & vbCrLf & _
                "ask = perguntar antes de abrir o agente" & vbCrLf & _
                "off = modo livre, sem perguntar" & vbCrLf & _
                "on  = modo secreto (em desenvolvimento)", TITULO, LerSecret(aviso))
            If StrPtr(v) = 0 Then Exit Sub
            v = LCase$(Trim$(v))
            If v <> "ask" And v <> "off" And v <> "on" Then
                MsgBox "Modo desconhecido: " & v & vbCrLf & "Use ask, off ou on.", vbExclamation, TITULO
                Exit Sub
            End If
            If GravarSecret(v) Then
                MsgBox "Modo gravado: " & DescreverModo(v) & vbCrLf & vbCrLf & _
                    "Vale tambem para o motor e para a skill:" & vbCrLf & Abreviar(ArquivoConfig()), vbInformation, TITULO
            End If
        Case "9"
            If MsgBox("Apagar a configuracao deste suplemento neste usuario?" & vbCrLf & vbCrLf & _
                "Os relatorios ja gravados nao sao apagados." & vbCrLf & _
                "O modo (item 5) nao muda aqui: ele e compartilhado com o motor e a skill.", _
                vbOKCancel + vbExclamation, TITULO) = vbOK Then
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
        If Not GravarUtf8(pasta & "\pedido.md", PedidoAnalise(base, pasta, py, rv)) Then Exit Sub
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
        If Not GravarUtf8(pasta & "\pedido.md", PedidoComparacao(baseAnt, baseAtu, pasta, py, rv)) Then Exit Sub
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
        motivo = "Nao encontrei nenhum agente no PATH (claude, codex, copilot, gemini, code)."
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
    ResolverAgente = ResolverModo(agente)
End Function

' ===================== modo: livre ou secreto =====================

' Decide o modo antes de o agente ser aberto e antes de qualquer XML ser exportado.
' Devolve True para seguir no modo LIVRE, False para nao abrir o agente.
' Nunca segue no modo livre calada quando o configurado e o secreto: ai a pessoa escolhe na hora.
Private Function ResolverModo(ByVal agente As String) As Boolean
    Dim aviso As String, cabeca As String
    Select Case LerSecret(aviso)
        Case "off"
            ResolverModo = True
        Case "on"
            ResolverModo = (MsgBox("O modo SECRETO e o padrao configurado, e ele ainda esta em desenvolvimento." & vbCrLf & vbCrLf & _
                "Quando existir, o agente vai ler so uma versao codificada do cronograma, e a " & _
                "decodificacao vai acontecer nesta maquina." & vbCrLf & vbCrLf & _
                "Hoje so existe o modo LIVRE: o que o agente (" & agente & ") ler vai para o provedor dele." & vbCrLf & _
                "Os botoes Sem IA geram o relatorio nesta maquina e nada sai dela." & vbCrLf & vbCrLf & _
                "Sim: abrir o agente no modo LIVRE, so desta vez." & vbCrLf & _
                "Nao: cancelar. Nada foi exportado.", vbYesNo + vbExclamation + vbDefaultButton2, TITULO) = vbYes)
        Case Else
            If aviso <> "" Then cabeca = aviso & vbCrLf & "Por isso a pergunta voltou." & vbCrLf & vbCrLf
            Select Case MsgBox(cabeca & "Modo LIVRE: o que o agente (" & agente & ") ler vai para o provedor dele. Continuar?" & vbCrLf & vbCrLf & _
                "Isso inclui o XML, os resultados e o que voce escrever, nas condicoes da sua conta ou da " & _
                "sua empresa. Confira se a politica da empresa permite. Se nao permitir, use os botoes " & _
                "Sem IA: o relatorio e gerado nesta maquina e nada sai dela." & vbCrLf & vbCrLf & _
                "O modo SECRETO, em que o agente le so uma versao codificada, esta em desenvolvimento." & vbCrLf & vbCrLf & _
                "Sim: continuar no modo livre, desta vez." & vbCrLf & _
                "Nao: continuar no modo livre e nao perguntar mais." & vbCrLf & _
                "Cancelar: nao abrir o agente.", vbYesNoCancel + vbQuestion, TITULO)
                Case vbYes
                    ResolverModo = True
                Case vbNo
                    ' Se a gravacao falhar, a mensagem ja apareceu e a pergunta volta na proxima vez.
                    GravarSecret "off"
                    ResolverModo = True
            End Select
    End Select
End Function

Private Function DescreverModo(ByVal v As String) As String
    Select Case v
        Case "off": DescreverModo = "off - livre, sem perguntar"
        Case "on": DescreverModo = "on - secreto (em desenvolvimento)"
        Case Else: DescreverModo = "ask - perguntar antes de abrir o agente"
    End Select
End Function

' CRONOAUDIT_CONFIG_DIR troca a pasta, como no motor.
Private Function PastaConfig() As String
    Dim p As String
    p = Environ$("CRONOAUDIT_CONFIG_DIR")
    If p = "" Then p = Environ$("USERPROFILE") & "\.cronoaudit"
    Do While Len(p) > 3 And Right$(p, 1) = "\"
        p = Left$(p, Len(p) - 1)
    Loop
    PastaConfig = p
End Function

Private Function ArquivoConfig() As String
    ArquivoConfig = PastaConfig() & "\config.json"
End Function

' Devolve ask, on ou off. Sem arquivo, ou sem a chave: ask, que e o padrao de fabrica, e aviso
' fica vazio. Arquivo ilegivel ou valor desconhecido: tambem ask, mas com o motivo em aviso.
' Uma preferencia que nao da para ler nunca vira "livre, sem perguntar".
Private Function LerSecret(ByRef aviso As String) As String
    Dim txt As String, soAscii As Boolean, ini As Long, fim As Long, v As String
    aviso = ""
    LerSecret = "ask"
    If Not ArquivoExiste(ArquivoConfig()) Then Exit Function
    If Not LerTextoAscii(ArquivoConfig(), txt, soAscii) Then
        aviso = "Nao consegui ler a configuracao do modo:" & vbCrLf & Abreviar(ArquivoConfig())
        Exit Function
    End If
    If Not PareceObjeto(txt) Then
        aviso = "A configuracao do modo esta ilegivel:" & vbCrLf & Abreviar(ArquivoConfig())
        Exit Function
    End If
    If InStr(1, txt, """secret""", vbBinaryCompare) = 0 Then Exit Function
    If Not AcharSecret(txt, ini, fim) Then
        aviso = "A configuracao do modo esta ilegivel:" & vbCrLf & Abreviar(ArquivoConfig())
        Exit Function
    End If
    v = LCase$(Trim$(Mid$(txt, ini, fim - ini + 1)))
    If v = "ask" Or v = "on" Or v = "off" Then
        LerSecret = v
    Else
        aviso = "A configuracao do modo tem um valor desconhecido (" & Left$(v, 20) & "):" & vbCrLf & Abreviar(ArquivoConfig())
    End If
End Function

' Grava a preferencia no arquivo compartilhado, em UTF-8 sem BOM. Troca so o valor da chave
' quando o arquivo esta legivel, para nao apagar outra chave que o motor venha a gravar.
' Grava num temporario e troca o nome: se algo falhar no meio, o pior caso e o arquivo sumir,
' e arquivo ausente vale "ask".
Private Function GravarSecret(ByVal valor As String) As Boolean
    Dim dest As String, tmp As String, txt As String, novo As String, resto As String
    Dim soAscii As Boolean, ini As Long, fim As Long, p As Long
    dest = ArquivoConfig()
    tmp = dest & ".tmp"
    novo = "{" & vbLf & "  ""secret"": """ & valor & """" & vbLf & "}" & vbLf
    If ArquivoExiste(dest) Then
        If LerTextoAscii(dest, txt, soAscii) Then
            If Not soAscii Then
                MsgBox "A configuracao do modo tem caracteres que este suplemento nao regrava com seguranca:" & vbCrLf & _
                    Abreviar(dest) & vbCrLf & vbCrLf & _
                    "Nada foi alterado. Grave pelo motor, num terminal:" & vbCrLf & _
                    "  review.py --secret " & valor, vbExclamation, TITULO
                Exit Function
            End If
            If PareceObjeto(txt) Then
                If AcharSecret(txt, ini, fim) Then
                    novo = Left$(txt, ini - 1) & valor & Mid$(txt, fim + 1)
                ElseIf InStr(1, txt, """secret""", vbBinaryCompare) = 0 Then
                    ' Objeto sem a chave: ela entra na frente do que ja existe.
                    p = InStr(txt, "{")
                    resto = Mid$(txt, p + 1)
                    If Mid$(resto, PularBrancos(resto, 1), 1) <> "}" Then
                        novo = "{" & vbLf & "  ""secret"": """ & valor & """," & resto
                    End If
                End If
            End If
        End If
    End If
    CriarPastas PastaConfig()
    If Not GravarUtf8(tmp, novo) Then Exit Function
    On Error Resume Next
    If ArquivoExiste(dest) Then Kill dest
    Err.Clear
    Name tmp As dest
    If Err.Number <> 0 Then
        Falha "gravar " & dest, Err
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    GravarSecret = True
End Function

' Leitura minima, de proposito: nao e um leitor de JSON. Acha a chave "secret" e devolve onde
' comeca e onde termina o valor dela, sem as aspas (posicoes a partir de 1).
Private Function AcharSecret(ByVal txt As String, ByRef ini As Long, ByRef fim As Long) As Boolean
    Dim p As Long, q As Long
    p = InStr(1, txt, """secret""", vbBinaryCompare)
    If p = 0 Then Exit Function
    p = PularBrancos(txt, p + 8)
    If Mid$(txt, p, 1) <> ":" Then Exit Function
    p = PularBrancos(txt, p + 1)
    If Mid$(txt, p, 1) <> """" Then Exit Function
    q = InStr(p + 1, txt, """")
    If q = 0 Then Exit Function
    ini = p + 1
    fim = q - 1
    AcharSecret = True
End Function

' Posicao do primeiro caractere, a partir de p, que nao e espaco, tabulacao ou fim de linha.
Private Function PularBrancos(ByVal txt As String, ByVal p As Long) As Long
    Do While p <= Len(txt)
        Select Case Asc(Mid$(txt, p, 1))
            Case 32, 9, 13, 10
                p = p + 1
            Case Else
                Exit Do
        End Select
    Loop
    PularBrancos = p
End Function

' O minimo para nao confiar num arquivo truncado: comeca com { e termina com }.
Private Function PareceObjeto(ByVal txt As String) As Boolean
    Dim a As Long, z As Long
    a = PularBrancos(txt, 1)
    z = Len(txt)
    Do While z > 0
        Select Case Asc(Mid$(txt, z, 1))
            Case 32, 9, 13, 10
                z = z - 1
            Case Else
                Exit Do
        End Select
    Loop
    If z <= a Then Exit Function
    PareceObjeto = (Mid$(txt, a, 1) = "{" And Mid$(txt, z, 1) = "}")
End Function

' Le o arquivo byte a byte como ASCII, pulando um BOM de UTF-8 na frente. soAscii = False se
' houver byte acima de 127; nesse caso o texto serve para ler a chave, mas nao para regravar.
Private Function LerTextoAscii(ByVal caminho As String, ByRef txt As String, ByRef soAscii As Boolean) As Boolean
    Dim f As Integer, b() As Byte, n As Long, i As Long, ini As Long
    txt = ""
    soAscii = True
    On Error Resume Next
    n = FileLen(caminho)
    If Err.Number <> 0 Or n > 65536 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    If n = 0 Then
        On Error GoTo 0
        LerTextoAscii = True
        Exit Function
    End If
    ReDim b(0 To n - 1)
    f = FreeFile
    Open caminho For Binary Access Read As #f
    If Err.Number = 0 Then Get #f, , b
    If Err.Number <> 0 Then
        Err.Clear
        Close #f
        On Error GoTo 0
        Exit Function
    End If
    Close #f
    On Error GoTo 0
    If n >= 3 Then
        If b(0) = &HEF And b(1) = &HBB And b(2) = &HBF Then ini = 3
    End If
    For i = ini To n - 1
        If b(i) > 127 Then
            soAscii = False
            txt = txt & "?"
        Else
            txt = txt & Chr$(b(i))
        End If
    Next i
    LerTextoAscii = True
End Function

' Abre um terminal visivel na pasta da rodada, com o agente iniciado sobre o pedido curto.
' cmd /k mantem a janela. Formas de chamada, cada uma conferida na documentacao do proprio CLI:
'   claude "PROMPT"        sessao interativa com pedido inicial
'   codex "PROMPT"         idem
'   copilot -i "PROMPT"    --interactive: sessao interativa que executa o pedido
'   gemini -i "PROMPT"     --prompt-interactive: executa o pedido e continua interativo
'   code "PASTA"           abre a pasta no VS Code; o pedido vai pela area de transferencia
Private Function AbrirAgente(ByVal agente As String, ByVal pasta As String) As Boolean
    Dim sh As Object, linha As String, cmd As String
    If agente = "code" Then
        AbrirAgente = AbrirVSCode(pasta)
        Exit Function
    End If
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

' O VS Code nao recebe pedido pela linha de comando. A pasta da rodada abre nele e a frase
' curta vai para a area de transferencia: a pessoa abre o Copilot Chat em modo agente e cola.
Private Function AbrirVSCode(ByVal pasta As String) As Boolean
    Dim sh As Object, copiou As Boolean
    copiou = CopiarParaAreaDeTransferencia(PROMPT_INICIAL)
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then
        Falha "abrir o VS Code (WScript.Shell bloqueado)", Err
        On Error GoTo 0
        Exit Function
    End If
    sh.Run "cmd /c code """ & pasta & """", 0, False
    If Err.Number <> 0 Then
        Falha "abrir o VS Code (a politica da maquina pode bloquear processos abertos por macro)", Err
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0
    If copiou Then
        MsgBox "O VS Code vai abrir na pasta da rodada." & vbCrLf & vbCrLf & _
            "1. Abra o Copilot Chat (Ctrl+Alt+I) e escolha o modo Agente." & vbCrLf & _
            "2. Cole o pedido com Ctrl+V e envie. Ele ja esta na area de transferencia:" & vbCrLf & vbCrLf & _
            "   " & PROMPT_INICIAL, vbInformation, TITULO
    Else
        MsgBox "O VS Code vai abrir na pasta da rodada." & vbCrLf & vbCrLf & _
            "1. Abra o Copilot Chat (Ctrl+Alt+I) e escolha o modo Agente." & vbCrLf & _
            "2. Nao consegui usar a area de transferencia. Digite o pedido:" & vbCrLf & vbCrLf & _
            "   " & PROMPT_INICIAL, vbInformation, TITULO
    End If
    AbrirVSCode = True
End Function

' Texto ASCII para a area de transferencia, pelo clip do Windows. chcp 1252 antes, para o
' clip ler o arquivo no mesmo codigo de pagina em que o VBA o gravou.
Private Function CopiarParaAreaDeTransferencia(ByVal txt As String) As Boolean
    Dim f As Integer, tmp As String, sh As Object, rc As Long
    tmp = Environ$("TEMP") & "\cronoaudit-prompt.txt"
    On Error Resume Next
    f = FreeFile
    Open tmp For Output As #f
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    Print #f, txt;
    Close #f
    Set sh = CreateObject("WScript.Shell")
    If Err.Number = 0 Then
        rc = sh.Run("cmd /c ""chcp 1252 >nul & clip < """ & tmp & """""", 0, True)
        If Err.Number = 0 Then CopiarParaAreaDeTransferencia = (rc = 0)
    End If
    Err.Clear
    Kill tmp
    Err.Clear
    On Error GoTo 0
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
        "- Idioma: portugues do Brasil (pt-BR). Converse e escreva em pt-BR, com acentuacao normal." & vbCrLf & _
        "- Modo: LIVRE. A pessoa confirmou no suplemento do MS Project, antes de este pedido ser gravado, " & _
        "que o que o agente ler vai para o provedor dele. Nao pergunte o modo de novo. " & _
        "(O modo secreto esta em desenvolvimento.)" & vbCrLf
End Function

' Os nomes exatos que o motor grava, para o agente nao adivinhar. baseAnterior vazio = analise
' de um arquivo so. Os tres ultimos da analise dependem do que o XML traz.
Private Function PedidoArquivos(ByVal baseAtual As String, ByVal baseAnterior As String) As String
    Dim s As String, r As String, c As String
    r = baseAtual & "-review"
    s = vbCrLf & "## Arquivos que o motor grava nesta pasta" & vbCrLf & vbCrLf & _
        "Use estes nomes exatamente. Nao procure outros." & vbCrLf & vbCrLf & _
        "Analise critica de `" & baseAtual & ".xml`:" & vbCrLf & vbCrLf & _
        "- `" & r & ".html`: o relatorio para a pessoa abrir" & vbCrLf & _
        "- `" & r & ".json`: achados e contagens (`counts` e o numero oficial)" & vbCrLf & _
        "- `" & r & "-readings.json`: as leituras prontas, por secao, e o bloco `inputs`" & vbCrLf & _
        "- `" & r & "-quality.json`: as quatorze metricas de qualidade da rede" & vbCrLf & _
        "- `" & r & "-forensics.json`: caminho condutor por marco, calendarios, padrao de execucao" & vbCrLf & _
        "- `" & r & "-scurve.json`: curva S e conciliacao com o arquivo" & vbCrLf & _
        "- `" & r & "-forecast.json`: Earned Schedule, look-ahead, ritmo, exposicao a chuva" & vbCrLf & _
        "- `" & r & "-productivity.json`: produtividade e tendencia por recurso" & vbCrLf
    If baseAnterior <> "" Then
        c = baseAnterior & "--to--" & baseAtual & "-cycle"
        s = s & vbCrLf & "Comparacao de `" & baseAnterior & ".xml` com `" & baseAtual & ".xml`:" & vbCrLf & vbCrLf & _
            "- `" & c & ".html`: o relatorio de ciclo para a pessoa abrir" & vbCrLf & _
            "- `" & c & ".json`: a comparacao inteira, como dado" & vbCrLf & _
            "- `" & c & "-readings.json`: as leituras prontas do ciclo, por secao" & vbCrLf
    End If
    s = s & vbCrLf & "Se algum destes nao existir depois de rodar, diga qual falta em vez de supor o conteudo." & vbCrLf
    PedidoArquivos = s
End Function

Private Function PedidoRegras(ByVal linhaDeComando As String, ByVal py As String, ByVal rv As String) As String
    PedidoRegras = vbCrLf & "## Como fazer" & vbCrLf & vbCrLf & _
        "1. Use a skill **cronoaudit**. Leia o SKILL.md dela antes de qualquer coisa e siga o que ele diz." & vbCrLf & _
        "2. Rode o motor da skill uma unica vez, gravando nesta pasta. O comando que ja funciona nesta maquina " & _
        "(o `--free` no fim diz ao motor que o modo ja foi escolhido):" & vbCrLf & vbCrLf & _
        "   ```" & vbCrLf & _
        "   " & linhaDeComando & vbCrLf & _
        "   ```" & vbCrLf & vbCrLf & _
        "   Python: `" & py & "`  |  review.py: `" & rv & "`" & vbCrLf & _
        "   (no PowerShell, um executavel entre aspas precisa de `&` na frente)" & vbCrLf & _
        "3. **Todo numero vem do motor.** Leia os arquivos JSON listados abaixo e cite as leituras prontas. " & _
        "Nao calcule nem estime por conta propria. Se um numero nao estiver nos arquivos, diga que nao esta. " & _
        "Ao apresentar, percentuais e pontos com duas casas." & vbCrLf & _
        "4. Diga o caminho completo do relatorio HTML gerado e resuma o que merece atencao, comecando " & _
        "pelos avisos que bloqueiam. Depois pergunte o que a pessoa quer aprofundar." & vbCrLf & _
        "5. Nao altere os XML. Nao rode a analise de novo sem que pecam ou sem que o arquivo mude." & vbCrLf & _
        "6. Personalizacao do relatorio ou do padrao da empresa: so quando pedirem, pelo fluxo que o SKILL.md descreve." & vbCrLf
End Function

Private Function PedidoAnalise(ByVal base As String, ByVal pasta As String, ByVal py As String, ByVal rv As String) As String
    PedidoAnalise = PedidoCabecalho("analise critica do cronograma") & _
        "- Arquivo: `" & base & ".xml` (nesta pasta; exportacao XML do MS Project, MSPDI)" & vbCrLf & _
        PedidoRegras(py & " """ & rv & """ """ & pasta & "\" & base & ".xml"" --outdir """ & pasta & """ --lang pt --free", py, rv) & _
        PedidoArquivos(base, "")
End Function

Private Function PedidoComparacao(ByVal baseAnterior As String, ByVal baseAtual As String, ByVal pasta As String, _
                                  ByVal py As String, ByVal rv As String) As String
    PedidoComparacao = PedidoCabecalho("comparacao de duas versoes do mesmo cronograma (relatorio de ciclo)") & _
        "- Versao ANTERIOR: `" & baseAnterior & ".xml` (nesta pasta)" & vbCrLf & _
        "- Versao ATUAL: `" & baseAtual & ".xml` (nesta pasta)" & vbCrLf & _
        "- A ordem importa: no comando, a anterior vem primeiro. O motor gera a analise critica da " & _
        "versao atual e o relatorio de ciclo entre as duas." & vbCrLf & _
        PedidoRegras(py & " """ & rv & """ """ & pasta & "\" & baseAnterior & ".xml"" """ & pasta & "\" & baseAtual & _
            ".xml"" --outdir """ & pasta & """ --lang pt --free", py, rv) & _
        PedidoArquivos(baseAtual, baseAnterior)
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
    ' --free: aqui nao ha agente e nada sai da maquina. Sem a chave, o motor perguntaria o modo
    ' no terminal, ou pararia quando o configurado e o secreto, que so diz respeito ao agente.
    cmd = py & " """ & rv & """ " & arquivos & " --outdir """ & pasta & """ --free"
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
    ' A v0.3 passa --free ao motor. Um motor anterior nao conhece a chave e pararia com erro.
    If Not ArquivoExiste(Left$(rv, InStrRev(rv, "\")) & "cronoaudit_config.py") Then
        MsgBox "A skill instalada e mais antiga que este suplemento (v0.3):" & vbCrLf & Abreviar(rv) & vbCrLf & vbCrLf & _
            "Rode de novo o instalador da cronoaudit para atualizar a skill.", vbCritical, TITULO
        Exit Function
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

' Troca o comeco de um caminho pelo nome da variavel de ambiente, para caber numa linha.
' %LOCALAPPDATA% antes de %USERPROFILE%: o primeiro fica dentro do segundo.
Private Function Abreviar(ByVal p As String) As String
    Dim v As Variant, raiz As String, aspa As String
    If Left$(p, 1) = """" Then
        aspa = """"
        p = Mid$(p, 2)
    End If
    For Each v In Array("LOCALAPPDATA", "USERPROFILE")
        raiz = Environ$(CStr(v))
        If Len(raiz) > 3 Then
            If LCase$(Left$(p, Len(raiz) + 1)) = LCase$(raiz & "\") Then
                Abreviar = aspa & "%" & CStr(v) & "%" & Mid$(p, Len(raiz) + 1)
                Exit Function
            End If
        End If
    Next v
    Abreviar = aspa & p
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
