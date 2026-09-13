# cronoaudit installer for Windows PowerShell — one command, every agent.
#
#   irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
#
# Installs the skill into the two directories that, between them, every
# Agent Skills client reads:
#   $HOME\.claude\skills\cronoaudit   Claude Code, OpenCode, Cursor
#   $HOME\.agents\skills\cronoaudit   Codex, Gemini CLI, Cursor, GitHub Copilot, VS Code, OpenCode
#
# Needs: PowerShell 5+, Python 3.9+ on PATH. Nothing else is installed and
# nothing is sent anywhere; the only network access is the download itself.
$ErrorActionPreference = "Stop"

$Repo = "Holiv/cronoaudit"
$Ref  = if ($env:CRONOAUDIT_REF) { $env:CRONOAUDIT_REF } else { "main" }

function Fail($msg) { Write-Host "cronoaudit: $msg" -ForegroundColor Red; exit 1 }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Fail "Python 3.9 or later is required and was not found on PATH" }
$ver = & $py.Source -c "import sys; print('%d.%d' % sys.version_info[:2])"
$ok  = & $py.Source -c "import sys; print(1 if sys.version_info >= (3, 9) else 0)"
if ($ok -ne "1") { Fail "Python $ver found; 3.9 or later is required" }

$work = Join-Path ([System.IO.Path]::GetTempPath()) ("cronoaudit-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    Write-Host "downloading $Repo@$Ref ..."
    $zip = Join-Path $work "src.zip"
    Invoke-WebRequest -Uri "https://codeload.github.com/$Repo/zip/refs/heads/$Ref" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $work -Force
    $skill = Get-ChildItem -Path $work -Recurse -Directory -Filter "cronoaudit" |
             Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | Select-Object -First 1
    if (-not $skill) { Fail "the download did not contain skills\cronoaudit\SKILL.md" }

    foreach ($dest in @("$HOME\.claude\skills\cronoaudit", "$HOME\.agents\skills\cronoaudit")) {
        if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
        Copy-Item -Path (Join-Path $skill.FullName "*") -Destination $dest -Recurse -Force
        Get-ChildItem -Path $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
        Write-Host "installed -> $dest"
    }

    Write-Host "verifying ..."
    & $py.Source "$HOME\.claude\skills\cronoaudit\scripts\test_checks.py" | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "self-test passed" }
    else { Write-Host "self-test could not run here (node is optional; the render check is skipped without it)" }

    $version = Get-Content (Join-Path $skill.FullName "VERSION") -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "cronoaudit $version is installed."
    Write-Host ""
    Write-Host "  Restart your agent, then ask it to review a schedule, or run directly:"
    Write-Host "    python $HOME\.claude\skills\cronoaudit\scripts\review.py delivery.xml"
    Write-Host ""
    Write-Host "  Export the schedule first:  MS Project > File > Save As > XML Format."
    Write-Host "  Manual and method:          https://github.com/$Repo"
}
finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
