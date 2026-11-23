# cronoaudit: instala (ou remove) a aba Cronoaudit no MS Project, no Windows.
#
#   irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/msproject/install-msproject.ps1 | iex
#
# Opcoes, definidas antes na mesma janela do PowerShell:
#   $env:CRONOAUDIT_MSPROJECT_REMOVE="1"   remove a aba e o modulo
#   $env:CRONOAUDIT_REF="branch"            instala de outra branch (padrao main)
#
# O que faz, na ordem (medido no Windows em 22/11/2026, Project 16 pt-BR):
#   1. guarda copia de cada Global.MPT e do arquivo da faixa de opcoes em
#      %LOCALAPPDATA%\cronoaudit\backup\<data>;
#   2. abre o Project como a pessoa abre (pelo atalho). Se o Project tiver um perfil de
#      servidor (Project Web App), ele pergunta o perfil: a pessoa escolhe "Computador".
#      A copia para o Global so funciona nesse perfil; o modulo copiado vale nos dois;
#   3. abre o modelo cronoaudit.mpt, que traz o modulo. O Project avisa sobre macros:
#      a pessoa clica "Desabilitar macros" (basta; nada roda do modelo);
#   4. copia o modulo para o Global.MPT (Organizador, por automacao) e fecha o Project
#      gravando o Global;
#   5. acrescenta a aba ao arquivo da faixa de opcoes
#      (%LOCALAPPDATA%\Microsoft\Office\MSProject.officeUI), sem apagar outras abas;
#   6. confere: abre o Project de novo por automacao e roda CronoauditPing.
# Nenhuma configuracao de seguranca do Office ou do Windows e alterada. Duas escolhas
# ficam com a pessoa, porque sao dela: o perfil e o aviso de macros.
$ErrorActionPreference = "Stop"
$Ref = if ($env:CRONOAUDIT_REF) { $env:CRONOAUDIT_REF } else { "main" }
$Remove = $env:CRONOAUDIT_MSPROJECT_REMOVE -eq "1"
$Raw = "https://raw.githubusercontent.com/Holiv/cronoaudit/$Ref/msproject"
$Module = "Cronoaudit"
$TabId = "mso_c1.Cronoaudit"
$UiPath = Join-Path $env:LOCALAPPDATA "Microsoft\Office\MSProject.officeUI"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Backup = Join-Path $env:LOCALAPPDATA "cronoaudit\backup\$Stamp"
$Work = Join-Path $env:TEMP "cronoaudit-msproject-$Stamp"

function Say([string]$s) { Write-Host $s }
function Step([string]$s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Fail([string]$s) { Write-Host ""; Write-Host "PAROU: $s" -ForegroundColor Red; throw "cronoaudit-msproject: $s" }
function Wait-Key([string]$s) { Write-Host $s -ForegroundColor Yellow; [void](Read-Host "Enter para continuar") }

# ---- 0. Project instalado e fechado
Step "Conferindo o MS Project"
$exe = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINPROJ.EXE" -ErrorAction SilentlyContinue).'(default)'
if (-not $exe -or -not (Test-Path $exe)) { Fail "o MS Project nao foi encontrado neste computador." }
Say "Project: $exe"
while (@(Get-Process WINPROJ -ErrorAction SilentlyContinue).Count -gt 0) {
    Wait-Key "O Project esta aberto. Salve o que precisar, feche o Project e aperte Enter."
}

# ---- 1. copias de seguranca
Step "Copias de seguranca em $Backup"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
$globals = @(Get-ChildItem -Path (Join-Path $env:APPDATA "Microsoft\MS Project") -Recurse -Filter "Global.MPT" -ErrorAction SilentlyContinue)
foreach ($g in $globals) {
    $rel = $g.FullName.Substring((Join-Path $env:APPDATA "Microsoft\MS Project").Length).TrimStart("\")
    $dest = Join-Path $Backup ("Global\" + $rel)
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item -LiteralPath $g.FullName -Destination $dest
    Say "Global.MPT: $($g.FullName)"
}
if (Test-Path $UiPath) { Copy-Item -LiteralPath $UiPath -Destination (Join-Path $Backup "MSProject.officeUI"); Say "faixa de opcoes: $UiPath" }
Say "Para desfazer tudo: copie esses arquivos de volta, com o Project fechado."

# ---- 2. os arquivos do suplemento
New-Item -ItemType Directory -Force -Path $Work | Out-Null
$here = if ($PSScriptRoot) { $PSScriptRoot } else { "" }
function Get-Part([string]$name) {
    $local = if ($here) { Join-Path $here $name } else { "" }
    $dest = Join-Path $Work $name
    if ($local -and (Test-Path $local)) { Copy-Item -LiteralPath $local -Destination $dest }
    else { Invoke-WebRequest -UseBasicParsing -Uri "$Raw/$name" -OutFile $dest }
    return $dest
}
$ui = Get-Part "cronoaudit.officeUI"
$mpt = if ($Remove) { $null } else { Get-Part "cronoaudit.mpt" }

# ---- 3. o Project, aberto como a pessoa abre
Step "Abrindo o Project"
Say "Se aparecer a janela de Logon com perfis, escolha 'Computador' e OK."
Start-Process -FilePath $exe
$app = $null
for ($i = 0; $i -lt 120 -and -not $app; $i++) {
    Start-Sleep -Seconds 2
    try { $app = New-Object -ComObject MSProject.Application; [void]$app.Projects.Count } catch { $app = $null }
}
if (-not $app) { Fail "o Project nao respondeu em 4 minutos." }
Wait-Key "Quando o Project estiver aberto (com um projeto em branco), aperte Enter."

try {
    try { $app.DisplayAlerts = $false } catch { }
    # O Organizador so funciona com um projeto aberto: sem nenhum (a tela inicial do
    # Project), OrganizerDeleteItem responde "O metodo nao esta disponivel nesta
    # situacao" (medido em 22/11/2026).
    if ($app.Projects.Count -eq 0) { [void]$app.FileNew() }

    if (-not $Remove) {
        Step "Copiando o modulo para o Global.MPT"
        Say "O Project vai avisar sobre macros no modelo: clique 'Desabilitar macros'."
        [void]$app.FileOpenEx($mpt, $false)
        # A versao anterior sai antes: o modulo novo entra no lugar, nao ao lado.
        try { [void]$app.OrganizerDeleteItem(3, "Global.MPT", $Module) } catch { }
        $ok = $app.OrganizerMoveItem(3, $app.ActiveProject.Name, "Global.MPT", $Module)
        try { [void]$app.FileCloseEx(0) } catch { }
        if (-not $ok) {
            Fail ("o Project nao deixou copiar o modulo. Isso acontece quando ele abre num perfil de " +
                  "servidor (Project Web App). Rode de novo e escolha 'Computador' na janela de Logon.")
        }
    } else {
        Step "Removendo o modulo do Global.MPT"
        try { $del = $app.OrganizerDeleteItem(3, "Global.MPT", $Module) } catch { $del = $false; Say "Project: $($_.Exception.Message)" }
        if (-not $del) { Say "O Project nao confirmou a remocao; confiro depois de fechar." }
    }
    while ($app.Projects.Count -gt 0) { try { [void]$app.FileCloseEx(0) } catch { break } }
    # 1 = pjSave: grava o Global ao sair. Com 0 a copia se perde (medido).
    $app.Quit(1)
} catch {
    try { $app.Quit(0) } catch { }
    throw
}
for ($i = 0; $i -lt 30 -and @(Get-Process WINPROJ -ErrorAction SilentlyContinue).Count -gt 0; $i++) { Start-Sleep -Seconds 1 }

# ---- 4. a aba, sem apagar as outras
Step "Aba Cronoaudit na faixa de opcoes"
$ns = "http://schemas.microsoft.com/office/2009/07/customui"
[xml]$ours = Get-Content -LiteralPath $ui -Raw -Encoding UTF8
if (Test-Path $UiPath) {
    [xml]$doc = Get-Content -LiteralPath $UiPath -Raw -Encoding UTF8
} else {
    [xml]$doc = '<mso:customUI xmlns:mso="http://schemas.microsoft.com/office/2009/07/customui"><mso:ribbon><mso:qat/><mso:tabs/></mso:ribbon></mso:customUI>'
}
$nsm = New-Object Xml.XmlNamespaceManager($doc.NameTable); $nsm.AddNamespace("mso", $ns)
$ribbon = $doc.SelectSingleNode("/mso:customUI/mso:ribbon", $nsm)
if (-not $ribbon) { $ribbon = $doc.DocumentElement.AppendChild($doc.CreateElement("mso", "ribbon", $ns)) }
$tabs = $ribbon.SelectSingleNode("mso:tabs", $nsm)
if (-not $tabs) { $tabs = $ribbon.AppendChild($doc.CreateElement("mso", "tabs", $ns)) }
foreach ($old in @($tabs.SelectNodes("mso:tab[@id='$TabId']", $nsm))) { [void]$tabs.RemoveChild($old) }
if (-not $Remove) {
    $nso = New-Object Xml.XmlNamespaceManager($ours.NameTable); $nso.AddNamespace("mso", $ns)
    $tab = $ours.SelectSingleNode("//mso:tab[@id='$TabId']", $nso)
    [void]$tabs.AppendChild($doc.ImportNode($tab, $true))
}
New-Item -ItemType Directory -Force -Path (Split-Path $UiPath) | Out-Null
$settings = New-Object Xml.XmlWriterSettings; $settings.Encoding = New-Object Text.UTF8Encoding($false)
$w = [Xml.XmlWriter]::Create($UiPath, $settings); $doc.Save($w); $w.Close()
Say "gravado: $UiPath"

# ---- 5. conferencia
if (-not $Remove) {
    Step "Conferindo"
    $ping = Join-Path $env:TEMP "cronoaudit-ping.txt"
    Remove-Item -LiteralPath $ping -ErrorAction SilentlyContinue
    $app = New-Object -ComObject MSProject.Application
    try { [void]$app.Macro("CronoauditPing") } catch { }
    try { $app.Quit(0) } catch { }
    if ((Test-Path $ping) -and ((Get-Content $ping -Raw) -match "Global")) {
        Say "OK: o modulo responde do Global.MPT."
    } else {
        Fail "o modulo nao respondeu. Copias de seguranca em $Backup."
    }
    Write-Host ""
    Write-Host "Pronto. Abra o Project: a aba 'Cronoaudit' fica entre 'Projeto' e 'Exibir'." -ForegroundColor Green
    Write-Host "Ela usa a skill cronoaudit; se ainda nao instalou, rode o instalador da cronoaudit." -ForegroundColor Green
} else {
    Step "Conferindo"
    $ping = Join-Path $env:TEMP "cronoaudit-ping.txt"
    Remove-Item -LiteralPath $ping -ErrorAction SilentlyContinue
    $app = New-Object -ComObject MSProject.Application
    $still = $true
    try { [void]$app.Macro("CronoauditPing") } catch { $still = $false }
    if (Test-Path $ping) { $still = $true } elseif ($still) { $still = $false }
    try { $app.Quit(0) } catch { }
    if ($still) { Fail "a aba saiu, mas o modulo continua no Global.MPT. Copias de seguranca em $Backup." }
    Write-Host ""
    Write-Host "Removido: aba e modulo. Copias de seguranca em $Backup." -ForegroundColor Green
}
Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
