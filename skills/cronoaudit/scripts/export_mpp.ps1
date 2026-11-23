# cronoaudit: export a schedule to XML through MS Project itself (Windows).
#
#   export_mpp.ps1 -Path <file.mpp> -Out <file.xml>     export a file on disk
#   export_mpp.ps1 -Active -Out <file.xml>              export the project open in Project
#
# Called by review.py when it is given a .mpp, so that nobody has to know what an
# XML export is. It uses the Project installed on this computer, the same way a
# person would: File > Save As > XML. Nothing is changed in the .mpp: a file on disk
# is opened read-only; an open project must be saved first, and is left open as it
# was. If Project was not running, it is started and closed again.
#
# Prints one line of JSON and nothing else: {"ok":..,"code":..,"source":..}. The
# caller keeps that line off the screen in secret mode, because a path can carry a
# name. No setting of Project, Office or Windows is changed.
param(
    [string]$Path = "",
    [switch]$Active,
    [Parameter(Mandatory = $true)][string]$Out
)
$ErrorActionPreference = "Stop"

function Done([bool]$ok, [string]$code, [string]$detail = "", [string]$source = "") {
    $o = [ordered]@{ ok = $ok; code = $code; detail = $detail; source = $source }
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

# Project is single-instance: if it is running, this is the person's own session.
$app = $null
$created = $false
try { $app = [Runtime.InteropServices.Marshal]::GetActiveObject("MSProject.Application") } catch { $app = $null }
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

$opened_here = $false
$was_open = $null
try {
    if ($Active) {
        if ($app.Projects.Count -eq 0) { Done $false "nothing_open" }
        $Path = $app.ActiveProject.FullName
        if ($Path -notmatch "\\") { Done $false "never_saved" }
    }
    if ($Path.ToLower().EndsWith(".xml")) { Done $false "already_xml" "" $Path }

    $was_open = IsOpen $Path
    if ($was_open) {
        if (-not $was_open.Saved) { Done $false "unsaved" "" $Path }
        $was_open.Activate()
    } else {
        Alerts $false
        $app.FileOpenEx($Path, $true, $m, $m, $m, $m, $m, $m, $m, $m, $m, $pjDoNotOpenPool) | Out-Null
        Alerts $true
        $opened_here = $true
        if ($app.ActiveProject.FullName -ine $Path) { Done $false "open_failed" "" $Path }
    }

    if (Test-Path -LiteralPath $Out) { Remove-Item -LiteralPath $Out -Force }
    Alerts $false
    $app.FileSaveAs($Out, $m, $m, $m, $m, $m, $m, $m, $m, "MSProject.XML") | Out-Null
    Alerts $true

    # Save As may switch the open document to the XML: close that, never saving.
    if ($app.Projects.Count -gt 0 -and $app.ActiveProject.FullName -ieq $Out) { CloseActive }
    if ($opened_here) {
        $left = IsOpen $Path
        if ($left) { $left.Activate(); CloseActive }
    } elseif ($was_open -and -not (IsOpen $Path)) {
        # The person had it open: put it back as it was.
        $app.FileOpenEx($Path) | Out-Null
    }
} catch {
    Alerts $true
    Done $false "export_failed" $_.Exception.Message $Path
} finally {
    if ($created) {
        try { if ($app.Projects.Count -eq 0) { $app.Quit($pjDoNotSave) } } catch { }
    }
}

if (-not (Test-Path -LiteralPath $Out) -or (Get-Item -LiteralPath $Out).Length -eq 0) {
    Done $false "export_empty" "" $Path
}
Done $true "ok" "" $Path
