# cronoaudit: export a schedule to XML through MS Project itself (Windows).
#
#   export_mpp.ps1 -Path <file.mpp> -Out <file.xml>     export a file on disk
#   export_mpp.ps1 -Active -Out <file.xml>              export the project open in Project
#
# Called by review.py when it is given a .mpp, so that nobody has to know what an
# XML export is. It uses the Project installed on this computer, the same way a
# person would: File > Save As > XML. Nothing is changed in the .mpp, and a project
# the person has open is never touched: the file as saved on disk is copied to a
# temporary folder and the copy is opened read-only, exported and closed. If
# Project was not running, it is started and closed again.
#
# Prints one line of JSON and nothing else: {"ok":..,"code":..,"source":..,
# "unsaved":..}. The caller keeps that line off the screen in secret mode, because a
# path can carry a name. No setting of Project, Office or Windows is changed.
#
# Measured on Windows (Project 16, pt-BR) on 22/11/2026:
# - FileSaveAs takes 0 in Format; [Type]::Missing there finds no overload. The
#   FormatID decides the format.
# - GetActiveObject can return a session with no projects while Project is open;
#   Project is single-instance, so New-Object returns the person's own session.
# - Opening a .mpp marks it unsaved even with nothing changed (Project recalculates):
#   "unsaved" cannot tell a change from a recalculation, hence the copy.
param(
    [string]$Path = "",
    [switch]$Active,
    [Parameter(Mandatory = $true)][string]$Out
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$script:unsaved = $false
function Done([bool]$ok, [string]$code, [string]$detail = "", [string]$source = "") {
    $o = [ordered]@{ ok = $ok; code = $code; detail = $detail; source = $source; unsaved = $script:unsaved }
    [Console]::Out.WriteLine(($o | ConvertTo-Json -Compress))
    if ($ok) { exit 0 } else { exit 1 }
}

$m = [Type]::Missing
$pjDoNotSave = 0
$pjDoNotOpenPool = 4

if (-not $Active -and -not $Path) { Done $false "no_input" "give -Path or -Active" }
if ($Path) {
    if (-not (Test-Path -LiteralPath $Path)) { Done $false "not_found" }
    $Path = (Resolve-Path -LiteralPath $Path).Path
}

$app = $null
$created = $false
$running = @(Get-Process WINPROJ -ErrorAction SilentlyContinue).Count -gt 0
if ($running) { try { $app = New-Object -ComObject MSProject.Application } catch { $app = $null } }
if (-not $app) {
    if ($Active) { Done $false "project_not_running" }
    try {
        $app = New-Object -ComObject MSProject.Application
        $created = $true
        # Visible, so that a question Project asks (a sign-in, a missing link) is
        # seen and answered instead of waiting behind the screen.
        $app.Visible = $true
    } catch { Done $false "no_project" $_.Exception.Message }
}

function Alerts([bool]$on) { try { $app.Alerts($on) } catch { } }
function IsOpen([string]$p) {
    foreach ($pr in $app.Projects) { if ($pr.FullName -ieq $p) { return $pr } }
    return $null
}
function CloseActive() {
    try { $app.FileCloseEx($pjDoNotSave) } catch { try { $app.FileClose($pjDoNotSave) } catch { } }
}
function CloseIfOpen([string]$p) {
    try { $left = IsOpen $p; if ($left) { $left.Activate(); CloseActive } } catch { }
}

$src = $null
$copydir = $null
try {
    if ($Active) {
        if ($app.Projects.Count -eq 0) { Done $false "nothing_open" }
        $Path = $app.ActiveProject.FullName
        if ($Path -notmatch "\\") { Done $false "never_saved" }
    }
    if ($Path.ToLower().EndsWith(".xml")) { Done $false "already_xml" "" $Path }

    $open = IsOpen $Path
    if ($open) {
        # The person's own window stays as it is. The file as saved on disk is what
        # the analysis reads; changes not yet saved are not in it, and the caller says so.
        $script:unsaved = -not $open.Saved
        $copydir = Join-Path ([IO.Path]::GetTempPath()) ("cronoaudit-copy-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
        New-Item -ItemType Directory -Path $copydir | Out-Null
        $src = Join-Path $copydir ([IO.Path]::GetFileNameWithoutExtension($Path) + " (cronoaudit).mpp")
        Copy-Item -LiteralPath $Path -Destination $src
    } else {
        $src = $Path
    }

    Alerts $false
    $app.FileOpenEx($src, $true, $m, $m, $m, $m, $m, $m, $m, $m, $m, $pjDoNotOpenPool) | Out-Null
    Alerts $true
    if ($app.ActiveProject.FullName -ine $src) { Done $false "open_failed" "" $Path }

    if (Test-Path -LiteralPath $Out) { Remove-Item -LiteralPath $Out -Force }
    Alerts $false
    $app.FileSaveAs($Out, 0, $m, $m, $m, $m, $m, $m, $m, "MSProject.XML") | Out-Null
    Alerts $true

    # Save As may switch the open document to the XML: close that, never saving.
    if ($app.Projects.Count -gt 0 -and $app.ActiveProject.FullName -ieq $Out) { CloseActive }
    CloseIfOpen $src
} catch {
    $err = $_.Exception.Message
    Alerts $true
    if ($src) { CloseIfOpen $src }
    CloseIfOpen $Out
    Done $false "export_failed" $err $Path
} finally {
    if ($copydir) { Remove-Item -LiteralPath $copydir -Recurse -Force -ErrorAction SilentlyContinue }
    if ($created) {
        try { if ($app.Projects.Count -eq 0) { $app.Quit($pjDoNotSave) } } catch { }
    }
}

if (-not (Test-Path -LiteralPath $Out) -or (Get-Item -LiteralPath $Out).Length -eq 0) {
    Done $false "export_empty" "" $Path
}
Done $true "ok" "" $Path
