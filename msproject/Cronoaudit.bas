Attribute VB_Name = "Cronoaudit"
' cronoaudit para MS Project - v0.1 (21/11/2026)
'
' Tres botoes:
'   CronoauditAuditar    exporta o XML do arquivo ativo, roda a cronoaudit e abre o relatorio.
'                        Nada sai da maquina.
'   CronoauditComparar   pede o outro cronograma (.mpp ou .xml), exporta por tras e roda a
'                        comparacao de versoes. Nada sai da maquina.
'   CronoauditConversar  abre o agente (Claude Code, Copilot, Codex, Gemini) na pasta da ultima
'                        auditoria. Aqui sim: o agente envia ao provedor dele o que ler.
'
' Precisa de Python 3.9+ e da skill instalada pelo install.ps1 da cronoaudit.
' Configuracao guardada em HKCU\Software\VB and VBA Program Settings\cronoaudit\config
'   python  comando do Python (ex.: py -3)      review  caminho do review.py
'   pasta   onde os relatorios sao gravados     ultimo  pasta da ultima auditoria
' CronoauditConfigurar mostra e permite trocar esses valores.

Option Explicit

Private Const APP As String = "cronoaudit"
Private Const SEC As String = "config"
Private Const TITULO As String = "cronoaudit"

' ===================== botoes =====================

Public Sub CronoauditAuditar()
    Dim origem As String, pasta As String, xmlAtual As String, py As String, rv As String
    If Not PreVoo(origem) Then Exit Sub
    If Not AcharMotor(py, rv) Then Exit Sub
    pasta = NovaPastaDeRodada(NomeBase(ActiveProject.Name))
    xmlAtual = pasta & "\" & NomeBase(ActiveProject.Name) & ".xml"
    If Not ExportarXml(xmlAtual, origem, True) Then Exit Sub
    If RodarMotor(py, rv, """" & xmlAtual & """", pasta) Then
        AbrirRelatorio pasta & "\" & NomeBase(ActiveProject.Name) & "-review.html"
    End If
End Sub

Public Sub CronoauditComparar()
    Dim origem As String, outro As String, pasta As String, py As String, rv As String
    Dim xmlAtivo As String, xmlOutro As String, ativoEhAtual As VbMsgBoxResult
    Dim baseAtivo As String, baseOutro As String
    If Not PreVoo(origem) Then Exit Sub
    If Not AcharMotor(py, rv) Then Exit Sub

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
    xmlAtivo = pasta & "\" & baseAtivo & ".xml"
    If Not ExportarXml(xmlAtivo, origem, True) Then Exit Sub

    If LCase$(Right$(outro, 4)) = ".xml" Then
        xmlOutro = pasta & "\" & baseOutro & ".xml"
        On Error Resume Next
        FileCopy outro, xmlOutro
        If Err.Number <> 0 Then Falha "copiar " & outro, Err: Exit Sub
        On Error GoTo 0
    Else
        xmlOutro = pasta & "\" & baseOutro & ".xml"
        If Not ExportarOutro(outro, xmlOutro, origem) Then Exit Sub
    End If

    Dim anterior As String, atual As String, baseAnt As String, baseAtu As String
    If ativoEhAtual = vbYes Then
        anterior = xmlOutro: atual = xmlAtivo: baseAnt = baseOutro: baseAtu = baseAtivo
    Else
        anterior = xmlAtivo: atual = xmlOutro: baseAnt = baseAtivo: baseAtu = baseOutro
    End If
    If RodarMotor(py, rv, """" & anterior & """ """ & atual & """", pasta) Then
        AbrirRelatorio pasta & "\" & baseAnt & "--to--" & baseAtu & "-cycle.html"
    End If
End Sub

Public Sub CronoauditConversar()
    Dim pasta As String, agente As String, prompt As String, sh As Object
    pasta = GetSetting(APP, SEC, "ultimo", "")
    If pasta = "" Or Dir(pasta, vbDirectory) = "" Then
        MsgBox "Ainda nao ha auditoria para conversar. Rode Auditar ou Comparar primeiro.", vbInformation, TITULO
        Exit Sub
    End If
    If MsgBox("A auditoria rodou so nesta maquina." & vbCrLf & vbCrLf & _
        "A conversa e diferente: o agente envia ao provedor dele o conteudo que ler " & _
        "(os resultados da pasta abaixo). Continuar?" & vbCrLf & vbCrLf & pasta, _
        vbOKCancel + vbExclamation, TITULO) <> vbOK Then Exit Sub

    prompt = "Use a skill cronoaudit. Os resultados ja foram gerados nesta pasta (" & pasta & _
        "). Nao rode a analise de novo: leia os JSON na ordem do relatorio, comece pelos avisos que bloqueiam, " & _
        "e me diga o que merece atencao."
    CopiarParaAreaDeTransferencia prompt

    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then Falha "abrir o terminal (WScript.Shell bloqueado)", Err: Exit Sub
    On Error GoTo 0
    agente = AcharAgente()
    Select Case agente
        Case "claude", "codex"
            sh.Run "cmd /k cd /d """ & pasta & """ && " & agente & " """ & Replace(prompt, """", "'") & """", 1, False
        Case "copilot", "gemini"
            sh.Run "cmd /k cd /d """ & pasta & """ && " & agente, 1, False
            MsgBox "O agente abriu na pasta da auditoria. O pedido inicial esta na area de transferencia: cole com Ctrl+V.", vbInformation, TITULO
        Case "code"
            sh.Run "cmd /c code """ & pasta & """", 0, False
            MsgBox "O VS Code abriu na pasta da auditoria. Abra o chat do Copilot no modo agente e cole o pedido (Ctrl+V).", vbInformation, TITULO
        Case Else
            sh.Run "cmd /k cd /d """ & pasta & """", 1, False
            MsgBox "Nenhum agente encontrado no PATH (claude, copilot, codex, gemini, code)." & vbCrLf & _
                "Abri um terminal na pasta da auditoria; o pedido inicial esta na area de transferencia.", vbInformation, TITULO
    End Select
End Sub

Public Sub CronoauditConfigurar()
    Dim v As String
    v = InputBox("Comando do Python (vazio = detectar de novo):", TITULO, GetSetting(APP, SEC, "python", ""))
    If StrPtr(v) = 0 Then Exit Sub
    If v = "" Then DeleteSettingSeguro "python" Else SaveSetting APP, SEC, "python", v
    v = InputBox("Caminho do review.py (vazio = detectar de novo):", TITULO, GetSetting(APP, SEC, "review", ""))
    If StrPtr(v) = 0 Then Exit Sub
    If v = "" Then DeleteSettingSeguro "review" Else SaveSetting APP, SEC, "review", v
    v = InputBox("Pasta dos relatorios:", TITULO, PastaRaiz())
    If StrPtr(v) = 0 Then Exit Sub
    If v <> "" Then SaveSetting APP, SEC, "pasta", v
End Sub

' ===================== etapas =====================

' Bloqueia antes de exportar: ha arquivo, esta em disco, sem alteracoes pendentes.
' Alteracoes pendentes importam porque o "Salvar como" troca o documento ativo e o
' original e reaberto do disco: sem salvar, a alteracao se perderia.
Private Function PreVoo(ByRef origem As String) As Boolean
    If Projects.Count = 0 Then
        MsgBox "Abra um cronograma primeiro.", vbExclamation, TITULO
        Exit Function
    End If
    origem = ActiveProject.FullName
    If InStr(origem, "\") = 0 Then
        MsgBox "Salve o cronograma em disco antes de auditar.", vbExclamation, TITULO
        Exit Function
    End If
    If LCase$(Right$(origem, 4)) = ".xml" Then
        MsgBox "O arquivo aberto ja e um XML. Abra o .mpp, ou rode a cronoaudit direto pelo terminal sobre este XML.", vbExclamation, TITULO
        Exit Function
    End If
    If Not ActiveProject.Saved Then
        Select Case MsgBox("O cronograma tem alteracoes nao salvas." & vbCrLf & vbCrLf & _
            "Sim: salvar agora e auditar." & vbCrLf & "Nao: cancelar.", vbYesNo + vbExclamation, TITULO)
            Case vbYes
                On Error Resume Next
                FileSave
                If Err.Number <> 0 Then
                    Falha "salvar o cronograma", Err
                    Exit Function
                End If
                On Error GoTo 0
                If Not ActiveProject.Saved Then
                    MsgBox "O cronograma nao foi salvo. Auditoria cancelada.", vbExclamation, TITULO
                    Exit Function
                End If
                origem = ActiveProject.FullName
            Case Else
                Exit Function
        End Select
    End If
    Dim i As Long
    For i = 1 To Projects.Count
        If Not Projects(i).Saved Then
            MsgBox "Ha outro cronograma aberto com alteracoes nao salvas:" & vbCrLf & Projects(i).FullName & vbCrLf & vbCrLf & _
                "Salve ou feche antes de auditar: a exportacao fecha e reabre arquivos.", vbExclamation, TITULO
            Exit Function
        End If
    Next i
    If ActiveProject.Subprojects.Count > 0 Then
        If MsgBox("Este arquivo e um mestre com " & ActiveProject.Subprojects.Count & _
            " subprojetos. A auditoria de um mestre e menos confiavel que a de cada subprojeto. Continuar?", _
            vbOKCancel + vbExclamation, TITULO) <> vbOK Then Exit Function
    End If
    PreVoo = True
End Function

' Grava o projeto ativo em XML (MSPDI). Se o "Salvar como" trocar o documento ativo para o
' XML, fecha o XML sem salvar e, se reabrir = True, reabre o original pelo caminho.
Private Function ExportarXml(ByVal destino As String, ByVal original As String, ByVal reabrir As Boolean) As Boolean
    Dim errNum As Long, errDesc As String
    If Dir(destino) <> "" Then Kill destino
    Application.Alerts False
    On Error Resume Next
    FileSaveAs Name:=destino, FormatID:="MSProject.XML"
    errNum = Err.Number: errDesc = Err.Description
    Err.Clear
    On Error GoTo 0
    Application.Alerts True

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

    If errNum <> 0 Or Dir(destino) = "" Then
        MsgBox "Nao consegui gravar o XML em:" & vbCrLf & destino & vbCrLf & vbCrLf & _
            "Erro " & errNum & ": " & errDesc & vbCrLf & vbCrLf & _
            "Se a politica da maquina bloqueia gravacao por macro, use Arquivo > Salvar como > XML e rode a cronoaudit pelo terminal.", _
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
        On Error GoTo 0
    End If
    If AtivarSeAberto(caminho) Then
        MsgBox "A outra versao ficou aberta (somente leitura). Feche sem salvar:" & vbCrLf & caminho, vbExclamation, TITULO
    End If
    If Not AtivarSeAberto(original) Then
        On Error Resume Next
        FileOpenEx Name:=original
        On Error GoTo 0
    End If
    ExportarOutro = ok
End Function

' Roda o review.py numa janela de terminal visivel e espera. Em erro, a janela fica aberta.
Private Function RodarMotor(ByVal py As String, ByVal rv As String, ByVal arquivos As String, ByVal pasta As String) As Boolean
    Dim sh As Object, cmd As String, rc As Long
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then Falha "abrir o terminal (WScript.Shell bloqueado)", Err: Exit Function
    On Error GoTo 0
    cmd = py & " """ & rv & """ " & arquivos & " --outdir """ & pasta & """"
    On Error Resume Next
    rc = sh.Run("cmd /c ""title cronoaudit && " & cmd & " || (echo. & echo A cronoaudit terminou com erro. & pause & exit /b 1)""", 1, True)
    If Err.Number <> 0 Then
        Falha "executar o Python (a politica da maquina pode bloquear processos abertos por macro)", Err
        Exit Function
    End If
    On Error GoTo 0
    If rc <> 0 Then
        MsgBox "A cronoaudit terminou com codigo " & rc & ". A mensagem dela ficou no terminal." & vbCrLf & vbCrLf & _
            "Comando:" & vbCrLf & cmd, vbExclamation, TITULO
        Exit Function
    End If
    SaveSetting APP, SEC, "ultimo", pasta
    RodarMotor = True
End Function

Private Sub AbrirRelatorio(ByVal html As String)
    If Dir(html) = "" Then
        MsgBox "A cronoaudit rodou, mas o relatorio esperado nao esta em:" & vbCrLf & html, vbExclamation, TITULO
        Shell "explorer.exe """ & Left$(html, InStrRev(html, "\") - 1) & """", vbNormalFocus
        Exit Sub
    End If
    Shell "explorer.exe """ & html & """", vbNormalFocus
End Sub

' ===================== descoberta =====================

Private Function AcharMotor(ByRef py As String, ByRef rv As String) As Boolean
    Dim c As Variant
    rv = GetSetting(APP, SEC, "review", "")
    If rv = "" Or Dir(rv) = "" Then
        rv = ""
        For Each c In Array(Environ$("USERPROFILE") & "\.claude\skills\cronoaudit\scripts\review.py", _
                            Environ$("USERPROFILE") & "\.agents\skills\cronoaudit\scripts\review.py")
            If Dir(c) <> "" Then rv = c: Exit For
        Next c
        If rv = "" Then
            MsgBox "Nao achei a cronoaudit instalada (review.py)." & vbCrLf & vbCrLf & _
                "Instale com o comando do README, ou informe o caminho em CronoauditConfigurar.", vbCritical, TITULO
            Exit Function
        End If
        SaveSetting APP, SEC, "review", rv
    End If

    py = GetSetting(APP, SEC, "python", "")
    If py <> "" Then
        If PythonServe(py) Then AcharMotor = True: Exit Function
    End If
    For Each c In Array("py -3", "python", "python3", """" & Environ$("LOCALAPPDATA") & "\cronoaudit\python\python.exe""")
        If PythonServe(CStr(c)) Then
            py = c
            SaveSetting APP, SEC, "python", py
            AcharMotor = True
            Exit Function
        End If
    Next c
    MsgBox "Nao achei Python 3.9 ou mais novo que a macro consiga executar." & vbCrLf & vbCrLf & _
        "Instale o Python, ou informe o comando em CronoauditConfigurar.", vbCritical, TITULO
End Function

' Verdadeiro se o comando executa um Python >= 3.9. O alias da Microsoft Store devolve 9009.
Private Function PythonServe(ByVal py As String) As Boolean
    Dim sh As Object, rc As Long
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    rc = sh.Run("cmd /c """ & py & " -c ""import sys; sys.exit(0 if sys.version_info >= (3, 9) else 3)""""", 0, True)
    If Err.Number <> 0 Then Exit Function
    PythonServe = (rc = 0)
End Function

Private Function AcharAgente() As String
    Dim sh As Object, c As Variant
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    For Each c In Array("claude", "copilot", "codex", "gemini", "code")
        If sh.Run("cmd /c where " & c & " >nul 2>&1", 0, True) = 0 Then
            If Err.Number = 0 Then AcharAgente = c: Exit Function
        End If
        Err.Clear
    Next c
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
    If Dir(p, vbNormal) = "" Then
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

' Pasta local por padrao (%LOCALAPPDATA%), fora do OneDrive: o relatorio tem dado da obra.
Private Function PastaRaiz() As String
    PastaRaiz = GetSetting(APP, SEC, "pasta", Environ$("LOCALAPPDATA") & "\cronoaudit\relatorios")
End Function

Private Function NovaPastaDeRodada(ByVal base As String) As String
    Dim raiz As String, p As String
    raiz = PastaRaiz()
    CriarPastas raiz
    p = raiz & "\" & Format(Now, "yyyy-mm-dd_hhnnss") & "_" & base
    CriarPastas p
    NovaPastaDeRodada = p
End Function

Private Sub CriarPastas(ByVal p As String)
    Dim partes() As String, i As Long, acc As String
    If Right$(p, 1) = "\" Then p = Left$(p, Len(p) - 1)
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

' Nome sem extensao e sem caracteres que atrapalham caminho ou linha de comando.
' Project.Name pode vir com ou sem ".mpp" (extensoes ocultas no Windows).
Private Function NomeBase(ByVal nome As String) As String
    Dim i As Long, ch As String, r As String
    If InStrRev(nome, ".") > 0 Then
        Select Case LCase$(Mid$(nome, InStrRev(nome, ".")))
            Case ".mpp", ".xml", ".mpt": nome = Left$(nome, InStrRev(nome, ".") - 1)
        End Select
    End If
    For i = 1 To Len(nome)
        ch = Mid$(nome, i, 1)
        If InStr("\/:*?""<>|&^%!", ch) > 0 Then r = r & "_" Else r = r & ch
    Next i
    NomeBase = Trim$(r)
End Function

Private Sub CopiarParaAreaDeTransferencia(ByVal txt As String)
    Dim f As Integer, tmp As String
    tmp = Environ$("TEMP") & "\cronoaudit-prompt.txt"
    f = FreeFile
    Open tmp For Output As #f
    Print #f, txt;
    Close #f
    On Error Resume Next
    CreateObject("WScript.Shell").Run "cmd /c chcp 1252 >nul & clip < """ & tmp & """", 0, True
    On Error GoTo 0
End Sub

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
