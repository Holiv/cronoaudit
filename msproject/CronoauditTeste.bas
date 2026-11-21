Attribute VB_Name = "modCronoauditTeste"
' cronoaudit - teste de viabilidade do plugin para MS Project
'
' Mede, na maquina onde roda, as tres coisas que decidem a arquitetura do plugin:
'   1. o Project grava XML por macro, e qual documento fica ativo depois do "Salvar como"
'   2. a macro consegue executar um processo externo e esperar o resultado
'   3. existe um Python 3.9+ que a macro consegue chamar
'
' Nao altera o seu .mpp. Exige que ele esteja salvo (sem alteracoes pendentes),
' porque o "Salvar como" pode trocar o documento ativo e o original e reaberto do disco.
' Tudo o que ele grava fica em %TEMP%\cronoaudit-teste. Ao final abre o log no Bloco de Notas.

Option Explicit

Private logTxt As String

Private Sub L(ByVal s As String)
    logTxt = logTxt & s & vbCrLf
End Sub

Public Sub CronoauditTeste()
    Dim pasta As String, original As String, xmlPath As String, depois As String
    Dim sh As Object, t As Double, n As Long

    logTxt = ""
    L "cronoaudit - teste de viabilidade - " & Format(Now, "yyyy-mm-dd hh:nn:ss")
    L "Project " & Application.Version & " | usuario " & Environ$("USERNAME") & " | perfil " & Environ$("USERPROFILE")
    L ""

    If Projects.Count = 0 Then
        MsgBox "Abra um cronograma antes de rodar o teste.", vbExclamation, "cronoaudit"
        Exit Sub
    End If

    pasta = Environ$("TEMP") & "\cronoaudit-teste"
    If Dir(pasta, vbDirectory) = "" Then MkDir pasta

    original = ActiveProject.FullName
    L "[0] Arquivo ativo: " & original & "   (se comecar com https://, e arquivo do OneDrive/SharePoint)"
    L "    Name: " & ActiveProject.Name & "   (sem .mpp = extensoes ocultas no Windows)"
    If InStr(original, "\") = 0 Then
        MsgBox "Salve o cronograma em disco antes do teste.", vbExclamation, "cronoaudit"
        Exit Sub
    End If
    If Not ActiveProject.Saved Then
        MsgBox "O cronograma tem alteracoes nao salvas. Salve antes do teste: o original pode ser reaberto do disco.", vbExclamation, "cronoaudit"
        Exit Sub
    End If

    ' ---------- 1. Exportar XML ----------
    xmlPath = pasta & "\teste.xml"
    If Dir(xmlPath) <> "" Then Kill xmlPath
    L ""
    L "[1] FileSaveAs para XML: " & xmlPath
    t = Timer
    Application.Alerts False
    On Error Resume Next
    FileSaveAs Name:=xmlPath, FormatID:="MSProject.XML"
    If Err.Number <> 0 Then L "    ERRO " & Err.Number & " (" & Err.Source & "): " & Err.Description
    Err.Clear
    On Error GoTo 0
    Application.Alerts True
    L "    tempo: " & Format(Timer - t, "0.00") & " s"
    If Dir(xmlPath) <> "" Then
        L "    XML gravado: SIM, " & FileLen(xmlPath) & " bytes"
    Else
        L "    XML gravado: NAO"
    End If
    depois = ActiveProject.FullName
    L "    documento ativo depois: " & depois
    If depois <> original Then
        L "    -> o 'Salvar como' TROCOU o documento ativo. Reabrindo o original."
        On Error Resume Next
        FileCloseEx Save:=pjDoNotSave
        If Err.Number <> 0 Then
            L "    FileCloseEx falhou (" & Err.Number & "), tentando FileClose"
            Err.Clear
            FileClose Save:=pjDoNotSave
        End If
        Err.Clear
        FileOpenEx Name:=original
        If Err.Number <> 0 Then L "    ERRO ao reabrir " & Err.Number & ": " & Err.Description
        Err.Clear
        On Error GoTo 0
        L "    ativo agora: " & ActiveProject.FullName
    Else
        L "    -> o documento ativo NAO mudou."
    End If

    ' ---------- 2 e 3. Processo externo e Python ----------
    L ""
    L "[2] Processo externo com espera (WScript.Shell.Run)"
    On Error Resume Next
    Set sh = CreateObject("WScript.Shell")
    If Err.Number <> 0 Then
        L "    ERRO ao criar WScript.Shell " & Err.Number & ": " & Err.Description
        Err.Clear
        On Error GoTo 0
        GoTo fim
    End If
    On Error GoTo 0
    Rodar sh, "cmd /c ver", pasta, "cmd"

    L ""
    L "[3] Python"
    Dim cands As Variant, i As Long
    cands = Array("py -3", "python", "python3", """" & Environ$("LOCALAPPDATA") & "\cronoaudit\python\python.exe""")
    For i = LBound(cands) To UBound(cands)
        Rodar sh, cands(i) & " -c ""import sys; print(sys.executable, sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 9) else 3)""", pasta, CStr(cands(i))
    Next i

fim:
    Dim f As Integer, logPath As String
    logPath = pasta & "\resultado.txt"
    f = FreeFile
    Open logPath For Output As #f
    Print #f, logTxt;
    Close #f
    On Error Resume Next
    Shell "notepad.exe """ & logPath & """", vbNormalFocus
    If Err.Number <> 0 Then MsgBox logTxt, vbInformation, "cronoaudit - resultado"
    On Error GoTo 0
End Sub

Private Sub Rodar(sh As Object, ByVal comando As String, ByVal pasta As String, ByVal rotulo As String)
    Dim saida As String, rc As Long, t As Double, f As Integer, linha As String, txt As String
    saida = pasta & "\saida.txt"
    If Dir(saida) <> "" Then Kill saida
    t = Timer
    On Error Resume Next
    rc = sh.Run("cmd /c """ & comando & " > """ & saida & """ 2>&1""", 0, True)
    If Err.Number <> 0 Then
        L "    " & rotulo & ": BLOQUEADO ao executar, erro " & Err.Number & ": " & Err.Description
        Err.Clear
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0
    If Dir(saida) <> "" Then
        f = FreeFile
        Open saida For Input As #f
        Do While Not EOF(f)
            Line Input #f, linha
            txt = txt & Trim$(linha) & " "
        Loop
        Close #f
    End If
    L "    " & rotulo & ": codigo de saida " & rc & " em " & Format(Timer - t, "0.00") & " s | " & Trim$(txt)
End Sub
