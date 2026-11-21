# cronoaudit installer for Windows PowerShell: one command, every agent.
#
#   In PowerShell:
#     irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
#
#   In cmd (the Command Prompt), where `irm` does not exist:
#     powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex"
#
# Installs the skill into the two directories that, between them, every
# Agent Skills client reads:
#   $HOME\.claude\skills\cronoaudit   Claude Code, OpenCode, Cursor
#   $HOME\.agents\skills\cronoaudit   Codex, Gemini CLI, Cursor, GitHub Copilot, VS Code, OpenCode
#
# Needs: PowerShell 5+ and Python 3.9+. When the machine has no working Python,
# the installer brings its own: the official CPython "embeddable package" from
# python.org, unpacked into %LOCALAPPDATA%\cronoaudit\python. No admin rights,
# no registry, no PATH change; deleting that folder removes it completely.
#
# Network access, all of it:
#   1. codeload.github.com   the repository zip (always)
#   2. www.python.org        the embeddable package (only when no Python is found,
#                            or when you ask for it), verified against the SHA-256
#                            pinned below before anything is unpacked
# Nothing is sent anywhere.
#
# Switches, as environment variables set before running:
#   $env:CRONOAUDIT_NO_PYTHON = "1"     never download Python; fail if none is found
#   $env:CRONOAUDIT_EMBED_PYTHON = "1"  use the bundled Python even if the machine has one
#   $env:CRONOAUDIT_REF = "branch"      install from another branch (default: main)
#
# This file is ASCII on purpose: Windows PowerShell 5 reads a script file without
# a byte-order mark in the machine's legacy code page.

# The bundled interpreter. Version, address and hash move together: to update,
# download the new zip, compute its SHA-256 yourself, and change all three.
# The hash below was computed from the file python.org serves at this address
# and equals the one published on the release page
# (https://www.python.org/downloads/release/python-31317/).
$CronoauditPyVersion = "3.13.17"
$CronoauditPyUrl     = "https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip"
$CronoauditPySha256  = "9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38"

function Invoke-CronoauditInstall {
    # Function scope, so nothing here changes the preferences of the session
    # that pasted the one-liner.
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"   # the progress bar makes PowerShell 5 downloads many times slower

    $Repo = "Holiv/cronoaudit"
    $Ref  = if ($env:CRONOAUDIT_REF) { $env:CRONOAUDIT_REF } else { "main" }
    $MinVersion = [version]"3.9"
    $EmbedDir = Join-Path $env:LOCALAPPDATA "cronoaudit\python"
    $EmbedExe = Join-Path $EmbedDir "python.exe"
    $noDownload = $env:CRONOAUDIT_NO_PYTHON -eq "1"
    $forceEmbed = $env:CRONOAUDIT_EMBED_PYTHON -eq "1"

    # Windows PowerShell 5 on an older system may still default to TLS 1.0,
    # which neither GitHub nor python.org accepts.
    try {
        [Net.ServicePointManager]::SecurityProtocol =
            [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    } catch { }

    function Get-PythonVersion([string]$Exe, [string[]]$Pre) {
        # The version a candidate REPORTS WHEN RUN, or $null. Finding a command
        # named python proves nothing: on a Windows with no Python, `python` and
        # `python3` are Microsoft Store aliases that exist, print a message and
        # exit 9009. So the candidate is executed, and anything but exit code 0
        # with a version on the first line counts as absent.
        $old = $ErrorActionPreference
        # With "Stop", Windows PowerShell 5 turns a native program's stderr into a
        # terminating error, which is exactly what the Store alias writes to.
        $ErrorActionPreference = "Continue"
        try {
            $global:LASTEXITCODE = 0
            $out = & $Exe @Pre -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
            if ($LASTEXITCODE -ne 0) { return $null }
            $line = "$($out | Select-Object -First 1)".Trim()
            if ($line -match '^\d+\.\d+\.\d+$') { return $line }
            return $null
        } catch {
            return $null   # the command does not exist, or could not start
        } finally {
            $ErrorActionPreference = $old
        }
    }

    function Install-EmbeddedPython([string]$Work) {
        if (-not [Environment]::Is64BitOperatingSystem) {
            throw "no Python was found, and the bundled one is 64-bit only. Install Python 3.9 or later (32-bit) from https://www.python.org/downloads/windows/ and run this again"
        }
        $zip = Join-Path $Work "python-embed.zip"
        Write-Host "downloading Python $CronoauditPyVersion (embeddable package) from python.org ..."
        Invoke-WebRequest -Uri $CronoauditPyUrl -OutFile $zip -UseBasicParsing
        $got = (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($got -ne $CronoauditPySha256.ToLowerInvariant()) {
            throw ("the Python download does not match the expected file, so it was NOT unpacked. " +
                   "Expected SHA-256 $CronoauditPySha256, got $got. " +
                   "This usually means a proxy replaced the download with a page of its own. " +
                   "Nothing was installed; install Python from https://www.python.org/downloads/windows/ instead, or try again on another network")
        }
        Write-Host "  SHA-256 verified: $got"
        # Unpack beside the destination and swap, so a failure half-way never
        # leaves a broken interpreter where the add-in looks for one.
        $stage = "$EmbedDir.new"
        if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
        New-Item -ItemType Directory -Path $stage -Force | Out-Null
        Expand-Archive -Path $zip -DestinationPath $stage -Force
        $ver = Get-PythonVersion (Join-Path $stage "python.exe") @()
        if ($ver -ne $CronoauditPyVersion) {
            Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
            throw ("the bundled Python was unpacked but does not run on this machine (expected $CronoauditPyVersion, got '$ver'). " +
                   "A security policy may be blocking programs under $env:LOCALAPPDATA. " +
                   "Install Python from https://www.python.org/downloads/windows/ instead")
        }
        if (Test-Path $EmbedDir) { Remove-Item -Recurse -Force $EmbedDir }
        Move-Item -Path $stage -Destination $EmbedDir
    }

    # ---- choose the interpreter, by running each candidate. Same order as the
    # MS Project add-in: the launcher, python, python3, then the bundled one.
    $py = $null
    if (-not $forceEmbed) {
        foreach ($c in @(
            @{ Exe = "py";      Pre = @("-3"); Label = "the Python launcher (py -3)" },
            @{ Exe = "python";  Pre = @();     Label = "python on PATH" },
            @{ Exe = "python3"; Pre = @();     Label = "python3 on PATH" }
        )) {
            $v = Get-PythonVersion $c.Exe $c.Pre
            if (-not $v) { continue }
            if ([version]$v -lt $MinVersion) {
                Write-Host "  skipping $($c.Label): Python $v, and 3.9 or later is required"
                continue
            }
            $where = (Get-Command $c.Exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
            $py = @{ Exe = $c.Exe; Pre = $c.Pre; Version = $v; Where = $where; Kind = "system: $($c.Label)" }
            break
        }
    }
    $needEmbed = -not $py

    $work = Join-Path ([System.IO.Path]::GetTempPath()) ("cronoaudit-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $work | Out-Null
    try {
        if ($needEmbed) {
            $have = if (Test-Path $EmbedExe) { Get-PythonVersion $EmbedExe @() } else { $null }
            if ($have -eq $CronoauditPyVersion) {
                Write-Host "bundled Python $have is already in place"
            } elseif ($noDownload) {
                if ($have -and ([version]$have -ge $MinVersion)) {
                    Write-Host "bundled Python $have is in place (an older one; CRONOAUDIT_NO_PYTHON is set, so it was not updated)"
                } elseif ($forceEmbed) {
                    throw "CRONOAUDIT_EMBED_PYTHON asks for the bundled Python and CRONOAUDIT_NO_PYTHON forbids downloading it. Unset one of them"
                } else {
                    throw "Python 3.9 or later is required and no working one was found (CRONOAUDIT_NO_PYTHON is set, so none was downloaded). Install it from https://www.python.org/downloads/windows/ or from the Microsoft Store"
                }
            } else {
                if ($forceEmbed) { Write-Host "CRONOAUDIT_EMBED_PYTHON is set: using the bundled Python" }
                else { Write-Host "no working Python 3.9+ was found on this machine (py, python and python3 were each run)" }
                Install-EmbeddedPython $work
            }
            $v = Get-PythonVersion $EmbedExe @()
            if (-not $v) { throw "the bundled Python at $EmbedExe does not run" }
            $py = @{ Exe = $EmbedExe; Pre = @(); Version = $v; Where = $EmbedExe; Kind = "bundled by this installer; no PATH or registry change" }
        }
        Write-Host "Python $($py.Version)  [$($py.Kind)]"
        Write-Host "  at $($py.Where)"

        Write-Host "downloading $Repo@$Ref ..."
        $zip = Join-Path $work "src.zip"
        Invoke-WebRequest -Uri "https://codeload.github.com/$Repo/zip/refs/heads/$Ref" -OutFile $zip -UseBasicParsing
        $src = Join-Path $work "src"
        Expand-Archive -Path $zip -DestinationPath $src -Force
        $skill = Get-ChildItem -Path $src -Recurse -Directory -Filter "cronoaudit" |
                 Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | Select-Object -First 1
        if (-not $skill) { throw "the download did not contain skills\cronoaudit\SKILL.md" }

        foreach ($dest in @("$HOME\.claude\skills\cronoaudit", "$HOME\.agents\skills\cronoaudit")) {
            if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
            New-Item -ItemType Directory -Path $dest -Force | Out-Null
            Copy-Item -Path (Join-Path $skill.FullName "*") -Destination $dest -Recurse -Force
            Get-ChildItem -Path $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
            Write-Host "installed -> $dest"
        }

        Write-Host "verifying ..."
        $review = "$HOME\.claude\skills\cronoaudit\scripts\review.py"
        $test   = "$HOME\.claude\skills\cronoaudit\scripts\test_checks.py"
        $pre = $py.Pre
        $ErrorActionPreference = "Continue"
        & $py.Exe @pre $test 2>$null | Out-Null
        $passed = $LASTEXITCODE -eq 0
        $ErrorActionPreference = "Stop"
        $call = if ($py.Exe -eq $EmbedExe) { "& `"$EmbedExe`"" } else { (@($py.Exe) + $pre) -join " " }
        if ($passed) { Write-Host "self-test passed" }
        else { Write-Host "self-test did NOT pass on this machine. To see why:  $call `"$test`"" -ForegroundColor Yellow }

        $version = Get-Content (Join-Path $skill.FullName "VERSION") -ErrorAction SilentlyContinue
        Write-Host ""
        Write-Host "cronoaudit $version is installed."
        Write-Host ""
        Write-Host "  Restart your agent, then ask it to review a schedule, or run directly:"
        Write-Host "    $call `"$review`" delivery.xml"
        Write-Host ""
        Write-Host "  Export the schedule first:  MS Project > File > Save As > XML Format."
        Write-Host "  Manual and method:          https://github.com/$Repo"
        if ($py.Exe -eq $EmbedExe) {
            Write-Host "  To remove the bundled Python: delete $(Split-Path $EmbedDir -Parent)"
        }
    }
    finally {
        Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
    }
}

# Run it, and report a failure WITHOUT closing the window. Pasted into an
# interactive PowerShell through `irm | iex`, this text runs in the session
# itself, so `exit` would close the window and take the message with it. A
# failure is therefore thrown inside the function and printed here. Only when
# this is a one-shot process (a .ps1 file, or powershell -Command from cmd) is
# an exit code set, because there the process ends anyway.
$CronoauditFailed = $false
try {
    Invoke-CronoauditInstall
} catch {
    $CronoauditFailed = $true
    Write-Host ""
    Write-Host "cronoaudit: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "cronoaudit: the installation did not finish. The manual route works everywhere: https://github.com/Holiv/cronoaudit#install" -ForegroundColor Red
}
if ($CronoauditFailed) {
    $CronoauditArgs = [Environment]::GetCommandLineArgs()
    $CronoauditOneShot = ($PSCommandPath -or ($CronoauditArgs -match '^[-/](c|co|com|comm|comma|comman|command|f|fi|fil|file|e|ec|en|enc|encodedcommand)$')) -and
                         -not ($CronoauditArgs -match '^[-/]noe(x(i(t)?)?)?$')
    if ($CronoauditOneShot) { exit 1 }
}
