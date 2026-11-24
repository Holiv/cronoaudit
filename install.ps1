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
#   $HOME\.agents\skills\cronoaudit   Codex, GitHub Copilot, and other Agent Skills clients
#
# Then, when MS Project is on the machine, it offers the Cronoaudit tab (the add-in
# installer, from the same branch), copies the fictitious example to
# $HOME\cronoaudit-exemplo and offers to run it, and says how to use the skill.
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
# The installer and the engine send nothing. An agent that later reads a schedule
# through the skill sends that content to its own provider.
#
# Switches, as environment variables set before running:
#   $env:CRONOAUDIT_NO_PYTHON = "1"     never download Python; fail if none is found
#   $env:CRONOAUDIT_EMBED_PYTHON = "1"  use the bundled Python even if the machine has one
#   $env:CRONOAUDIT_REF = "branch"      install from another branch (default: main)
#   $env:CRONOAUDIT_PLUGIN = "0" or "1"  the Project tab: do not ask, and skip or install it
#   $env:CRONOAUDIT_EXAMPLE = "0" or "1" the example: do not ask, and skip or run it
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

# Messages in Portuguese on a Portuguese Windows. The file stays ASCII, so an accent
# is written as a short code, {a~} for a-tilde and so on, and turned into the letter here.
$CronoauditPt = ([System.Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName -eq "pt")
function CronoauditText([string]$PtText, [string]$EnText) {
    if (-not $CronoauditPt) { return $EnText }
    $codes = @(@("a'", 0xE1), @("e'", 0xE9), @("i'", 0xED), @("o'", 0xF3), @("u'", 0xFA),
               @("a~", 0xE3), @("o~", 0xF5), @("a^", 0xE2), @("e^", 0xEA), @("o^", 0xF4),
               @("c,", 0xE7), @("E'", 0xC9))
    foreach ($c in $codes) { $PtText = $PtText.Replace("{" + $c[0] + "}", [string][char]$c[1]) }
    return $PtText
}

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

        Write-Host (CronoauditText "Baixando a cronoaudit ($Ref)..." "downloading $Repo@$Ref ...")
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
            Write-Host (CronoauditText "instalada em $dest" "installed -> $dest")
        }

        # The fictitious example, where a person can find it and open it in Project.
        # Copied before the self-test, which runs part of its checks on it.
        $exDest = Join-Path $HOME "cronoaudit-exemplo"
        $root = Get-ChildItem -Path $src -Directory | Select-Object -First 1
        $exSrc = if ($root) { Join-Path $root.FullName "examples" } else { "" }
        $exFiles = @()
        if ($exSrc -and (Test-Path $exSrc)) {
            $exFiles = @(Get-ChildItem -Path $exSrc -File | Where-Object { $_.Name -like "rodovia-ficticia-rev0*" -and $_.Extension -in ".xml", ".mpp" })
        }
        if ($exFiles.Count -gt 0) {
            New-Item -ItemType Directory -Path $exDest -Force | Out-Null
            foreach ($f in $exFiles) { Copy-Item -LiteralPath $f.FullName -Destination $exDest -Force }
            Write-Host (CronoauditText "exemplo fict{i'}cio em $exDest" "fictitious example -> $exDest")
        }

        Write-Host (CronoauditText "Conferindo..." "verifying ...")
        $review = "$HOME\.claude\skills\cronoaudit\scripts\review.py"
        $test   = "$HOME\.claude\skills\cronoaudit\scripts\test_checks.py"
        $pre = $py.Pre
        $ErrorActionPreference = "Continue"
        & $py.Exe @pre $test 2>$null | Out-Null
        $passed = $LASTEXITCODE -eq 0
        $ErrorActionPreference = "Stop"
        $call = if ($py.Exe -eq $EmbedExe) { "& `"$EmbedExe`"" } else { (@($py.Exe) + $pre) -join " " }
        if ($passed) { Write-Host (CronoauditText "Autoteste: tudo certo." "self-test passed") }
        else { Write-Host (CronoauditText "O autoteste n{a~}o passou neste computador. Para ver por qu{e^}:  $call `"$test`"" "self-test did NOT pass on this machine. To see why:  $call `"$test`"") -ForegroundColor Yellow }

        # The Project tab, offered only where Project is installed. It is the add-in's own
        # installer, from the same branch, in a scope of its own; if it fails, the skill
        # stays installed and the message says so.
        $tabDone = $false
        $tabUrl = "https://raw.githubusercontent.com/$Repo/$Ref/msproject/install-msproject.ps1"
        $winproj = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINPROJ.EXE" -ErrorAction SilentlyContinue).'(default)'
        $wantTab = $env:CRONOAUDIT_PLUGIN
        if ($winproj -and (Test-Path $winproj) -and $wantTab -ne "0") {
            if ($wantTab -ne "1") {
                Write-Host ""
                $ans = Read-Host (CronoauditText "O MS Project est{a'} instalado. Instalar tamb{e'}m a aba Cronoaudit no Project? [S/n]" "MS Project is installed. Also install the Cronoaudit tab in Project? [Y/n]")
                $wantTab = if ($ans -match '^\s*(n|nao|no)') { "0" } else { "1" }
            }
            if ($wantTab -eq "1") {
                $oldRef = $env:CRONOAUDIT_REF
                try {
                    $tabScript = (Invoke-WebRequest -UseBasicParsing -Uri $tabUrl).Content
                    $env:CRONOAUDIT_REF = $Ref
                    & ([scriptblock]::Create($tabScript))
                    $tabDone = $true
                } catch {
                    Write-Host ""
                    Write-Host (CronoauditText "A aba n{a~}o foi instalada: $($_.Exception.Message)" "The tab was not installed: $($_.Exception.Message)") -ForegroundColor Yellow
                    Write-Host (CronoauditText "A cronoaudit est{a'} instalada. Para tentar a aba de novo:  irm $tabUrl | iex" "cronoaudit is installed. To try the tab again:  irm $tabUrl | iex")
                } finally {
                    $env:CRONOAUDIT_REF = $oldRef
                }
            }
        }

        # The example, offered once: fictitious data, free mode, the report in the browser.
        $wantEx = $env:CRONOAUDIT_EXAMPLE
        if ($exFiles.Count -gt 0 -and $wantEx -ne "0") {
            if ($wantEx -ne "1") {
                Write-Host ""
                $ans = Read-Host (CronoauditText "Quer ver um exemplo agora? Ele analisa uma obra fict{i'}cia e abre o relat{o'}rio no navegador. [S/n]" "Would you like to see an example now? It analyses a fictitious works and opens the report in your browser. [Y/n]")
                $wantEx = if ($ans -match '^\s*(n|nao|no)') { "0" } else { "1" }
            }
            if ($wantEx -eq "1") {
                $ErrorActionPreference = "Continue"
                & $py.Exe @pre $review --example
                $ErrorActionPreference = "Stop"
            }
        }

        $version = Get-Content (Join-Path $skill.FullName "VERSION") -ErrorAction SilentlyContinue
        Write-Host ""
        Write-Host (CronoauditText "Pronto: cronoaudit $version instalada." "cronoaudit $version is installed.") -ForegroundColor Green
        Write-Host ""
        Write-Host (CronoauditText "Com um agente de IA (Claude Code, Copilot ou Codex): abra o agente na pasta do cronograma e pe{c,}a, por exemplo, ""analise o Rev04.mpp"". Se ele j{a'} estava aberto, feche e abra de novo." "With an AI agent (Claude Code, Copilot or Codex): open the agent in the schedule's folder and ask, for example, ""review Rev04.mpp"". If it was already open, close it and open it again.")
        if ($tabDone) {
            Write-Host (CronoauditText "No Project, a aba Cronoaudit fica entre Projeto e Exibir." "In Project, the Cronoaudit tab sits between Project and View.")
        }
        Write-Host ""
        Write-Host (CronoauditText "Sem agente, neste PowerShell:" "With no agent, in this PowerShell:")
        Write-Host "    $call `"$review`" `"$(CronoauditText 'C:\caminho\do\cronograma.mpp' 'C:\path\to\schedule.mpp')`""
        if ($exFiles.Count -gt 0) {
            Write-Host (CronoauditText "Para ver o exemplo de novo:" "To see the example again:")
            Write-Host "    $call `"$review`" --example"
        }
        Write-Host ""
        Write-Host (CronoauditText "Manual e ajuda: https://github.com/$Repo" "Manual and help: https://github.com/$Repo")
        if ($py.Exe -eq $EmbedExe) {
            Write-Host (CronoauditText "Para remover o Python que veio com a cronoaudit, apague $(Split-Path $EmbedDir -Parent)" "To remove the bundled Python: delete $(Split-Path $EmbedDir -Parent)")
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
    Write-Host (CronoauditText "cronoaudit: a instala{c,}{a~}o n{a~}o terminou. O passo a passo manual est{a'} em https://github.com/Holiv/cronoaudit#instalar" "cronoaudit: the installation did not finish. The manual route works everywhere: https://github.com/Holiv/cronoaudit#install") -ForegroundColor Red
}
if ($CronoauditFailed) {
    $CronoauditArgs = [Environment]::GetCommandLineArgs()
    $CronoauditOneShot = ($PSCommandPath -or ($CronoauditArgs -match '^[-/](c|co|com|comm|comma|comman|command|f|fi|fil|file|e|ec|en|enc|encodedcommand)$')) -and
                         -not ($CronoauditArgs -match '^[-/]noe(x(i(t)?)?)?$')
    if ($CronoauditOneShot) { exit 1 }
}
