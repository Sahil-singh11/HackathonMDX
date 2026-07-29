<#
.SYNOPSIS
    Lamer Konekte - one command to run the whole thing.

.DESCRIPTION
    PowerShell entry point for Windows. scripts/start.sh is the bash equivalent
    (Linux/WSL/Git Bash); this exists because PowerShell is the default shell on
    Windows and the README's `.venv/bin/...` paths are Linux-only - on Windows a
    venv puts its interpreter in `.venv\Scripts\`.

    Unlike the bash script this one SETS ITSELF UP: a missing venv, missing
    backend dependencies or missing node_modules are installed rather than
    reported as an error, so a fresh clone reaches a running app in one command.

.PARAMETER Prod
    Build the frontend and let the backend serve it from a single port. This is
    the only mode where the service worker runs, so it is the one to use when
    testing offline / PWA behaviour.

.PARAMETER Stop
    Stop whatever this script started (and any orphan holding the ports).

.PARAMETER Status
    Report what is running. Changes nothing.

.PARAMETER Test
    Backend pytest + frontend production build. What to run before pushing.

.PARAMETER Audit
    Start the app, then run the design-system accessibility audit
    (frontend/scripts/design-audit.mjs) against it.

.PARAMETER AuditChecks
    Which audit checks to run. Defaults to the fast set (~1 min). The contrast
    and scaling sweeps cover 108 screen states and take several minutes, so they
    are opt-in:  .\run.ps1 -Audit -AuditChecks contrast,scaling

.EXAMPLE
    .\run.ps1
    Dev mode: backend on :8000, Vite on :5173, browser opens on :5173.

.EXAMPLE
    .\run.ps1 -Prod
    Production: one port, service worker active.

.EXAMPLE
    .\run.ps1 -Stop
#>
[CmdletBinding()]
param(
    [switch]$Prod,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Test,
    [switch]$Audit,
    [string]$AuditChecks = 'headings,touch,typography,motion',
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [string]$BindHost = '127.0.0.1',
    [switch]$NoBrowser
)

# Deliberately NOT 'Stop'. This script shells out to python, pip, npm and
# netsh, and all of them write ordinary progress and warnings to stderr. Under
# PowerShell 5.1 a native command's stderr becomes a NativeCommandError
# ErrorRecord *as soon as the output is redirected or piped* — so with 'Stop'
# the script died on `python -m venv` printing a harmless "environment location
# may have moved" notice, but only when run inside a job or with output
# captured. It worked interactively, which is the worst kind of bug.
# Correctness comes from explicit $LASTEXITCODE checks after every native call,
# plus -ErrorAction Stop on the individual cmdlets whose failures we catch.
$ErrorActionPreference = 'Continue'
$Root   = $PSScriptRoot
$RunDir = Join-Path $Root '.run'

# PowerShell 5.1: no ternary, no ??, no &&/||. Keep to if/else and ';'.

function Say([string]$k, [string]$v) { Write-Host ("  {0,-13} {1}" -f $k, $v) }
function Head([string]$t) { Write-Host ""; Write-Host "=== $t ===" -ForegroundColor Cyan }
function Warn([string]$m) { Write-Host "  ! $m" -ForegroundColor Yellow }
function Die([string]$m)  { Write-Host ""; Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

function Get-VenvPython {
    # Windows venvs use Scripts\; keep the POSIX path as a fallback so this also
    # works if the venv was created under WSL against the same checkout.
    $win = Join-Path $Root 'backend\.venv\Scripts\python.exe'
    if (Test-Path $win) { return $win }
    $nix = Join-Path $Root 'backend/.venv/bin/python'
    if (Test-Path $nix) { return $nix }
    return $null
}

function Get-ListenerPids([int]$Port) {
    # Get-NetTCPConnection is the reliable path; netstat is the fallback for
    # locked-down boxes where the NetTCPIP module is unavailable.
    try {
        $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return @($c | Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {
        $out = netstat -ano | Select-String -Pattern "TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)"
        $ids = @()
        foreach ($m in $out) { $ids += [int]$m.Matches[0].Groups[1].Value }
        return @($ids | Select-Object -Unique)
    }
}

function Get-ExcludedPortRanges {
    # THE WinError 10013 TRAP. Windows (Hyper-V / WSL / Docker) reserves blocks of
    # TCP ports; binding inside one fails with "An attempt was made to access a
    # socket in a way forbidden by its access permissions" - which reads like a
    # firewall problem and sends you hunting in the wrong place. The port is not
    # in use, it is administratively excluded, so `netstat` shows nothing.
    $ranges = @()
    try {
        $raw = netsh interface ipv4 show excludedportrange protocol=tcp
        foreach ($line in $raw) {
            if ($line -match '^\s*(\d+)\s+(\d+)') {
                $ranges += [pscustomobject]@{ Start = [int]$Matches[1]; End = [int]$Matches[2] }
            }
        }
    } catch { }
    return $ranges
}

function Test-PortExcluded([int]$Port) {
    foreach ($r in (Get-ExcludedPortRanges)) {
        if ($Port -ge $r.Start -and $Port -le $r.End) { return $true }
    }
    return $false
}

function Resolve-UsablePort([int]$Port, [string]$Label) {
    # Walks upward past ports that are in use OR inside a Windows exclusion range,
    # so a reserved range never turns into a confusing 10013 crash.
    $p = $Port
    for ($i = 0; $i -lt 40; $i++) {
        $busy = @(Get-ListenerPids $p).Count -gt 0
        $excl = Test-PortExcluded $p
        if (-not $busy -and -not $excl) {
            if ($p -ne $Port) { Warn "$Label port $Port unavailable - using $p instead" }
            return $p
        }
        if ($excl) { Warn "port $p is inside a Windows reserved range (would fail as WinError 10013)" }
        else       { Warn "port $p is already in use" }
        $p++
    }
    Die "could not find a free $Label port near $Port. Try -$Label" + "Port <n>."
}

function Wait-Http([string]$Url, [int]$Seconds, [string[]]$LogPaths) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        } catch { Start-Sleep -Milliseconds 700 }
    }
    # Tail BOTH streams. uvicorn writes its startup banner and tracebacks to
    # stdout, so showing only the stderr log printed an empty section and hid
    # the actual reason the server never came up.
    foreach ($p in $LogPaths) {
        if ($p -and (Test-Path $p) -and (Get-Item $p).Length -gt 0) {
            Write-Host ""
            Write-Host "--- last 25 lines of $p ---" -ForegroundColor Yellow
            Get-Content $p -Tail 25
        }
    }
    return $false
}

function Stop-Tree([int]$ProcessId) {
    # taskkill /T takes the children too, which matters because `npm run dev`
    # spawns node as a child and killing only npm leaves Vite holding the port.
    taskkill /PID $ProcessId /T /F 2>$null | Out-Null
    Start-Sleep -Milliseconds 200
    try { Stop-Process -Id $ProcessId -Force -ErrorAction Stop } catch { }
}

function Invoke-StopAll {
    Head 'stopping'
    $stopped = $false
    foreach ($name in @('backend', 'frontend')) {
        $pidFile = Join-Path $RunDir "$name.pid"
        if (Test-Path $pidFile) {
            $raw = (Get-Content $pidFile -Raw).Trim()
            if ($raw -match '^\d+$') {
                $procId = [int]$raw
                if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
                    Stop-Tree $procId; Say $name "stopped (pid $procId)"; $stopped = $true
                }
            }
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
    }
    # Port sweep catches orphans and servers someone started by hand.
    foreach ($entry in @(@{n='backend';p=$BackendPort}, @{n='frontend';p=$FrontendPort})) {
        foreach ($procId in (Get-ListenerPids $entry.p)) {
            Stop-Tree $procId; Say $entry.n "stopped orphan on :$($entry.p) (pid $procId)"; $stopped = $true
        }
    }
    if (-not $stopped) { Say 'status' 'nothing was running' }
    Start-Sleep -Seconds 1
    $left = @()
    foreach ($p in @($BackendPort, $FrontendPort)) {
        if (@(Get-ListenerPids $p).Count -gt 0) { $left += $p }
    }
    if ($left.Count -gt 0) { Warn ("still held: " + ($left -join ', ')) } else { Write-Host "  All project ports are free." }
}

function Invoke-Status {
    Head 'status'
    foreach ($entry in @(@{n="backend  :$BackendPort";p=$BackendPort}, @{n="frontend :$FrontendPort";p=$FrontendPort})) {
        $ids = @(Get-ListenerPids $entry.p)
        if ($ids.Count -gt 0) { Say $entry.n ("running (pid " + ($ids -join ', ') + ")") }
        else { Say $entry.n 'not running' }
    }
}

# --------------------------------------------------------------- setup (idempotent)

function Initialize-Backend {
    $py = Get-VenvPython
    if (-not $py) {
        Say 'backend' 'no venv - creating one (first run only, ~1-2 min)'
        $sys = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $sys) { Die "Python not found on PATH. Install Python 3.12, then re-run." }
        # If the checkout lives in OneDrive, warn once. OneDrive and Defender
        # both scan a freshly created venv, which holds file handles open long
        # enough that deleting or renaming .venv fails with "being used by
        # another process" for a minute or two afterwards. Nothing here is
        # broken by that, but it makes a failed install painful to clean up.
        if ($Root -match 'OneDrive') {
            Warn 'this checkout is inside OneDrive; if venv cleanup ever fails with'
            Warn '"file in use", pause OneDrive sync or wait ~1 min and retry.'
        }
        Push-Location (Join-Path $Root 'backend')
        try {
            & $sys -m venv .venv
            if ($LASTEXITCODE -ne 0) { Die "could not create the virtualenv." }
        } finally { Pop-Location }
        $py = Get-VenvPython
        if (-not $py) { Die "venv created but no interpreter found inside it." }
    }
    # Cheap import probe: cheaper than pip install every run, and correct because
    # a half-installed venv fails here rather than at uvicorn startup.
    & $py -c "import fastapi, uvicorn, sqlmodel" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Say 'backend' 'installing dependencies (first run only)'
        Push-Location (Join-Path $Root 'backend')
        try {
            & $py -m pip install --disable-pip-version-check -r requirements.txt
        } finally { Pop-Location }
        # Re-probe rather than trusting pip's exit code. A flaky network can
        # leave pip reporting success after retries while a package is still
        # missing; without this the script went on to launch uvicorn and failed
        # with "backend did not become healthy", which points at the wrong
        # thing entirely. Verify the imports we actually need.
        & $py -c "import fastapi, uvicorn, sqlmodel" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Die @"
backend dependencies are still not importable after pip install.

The most common cause is a dropped connection to PyPI (look for
'ConnectionResetError' or 'Retrying' above). Re-run this script - pip resumes
from what it already downloaded.

To install by hand:
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
"@
        }
    }
    return $py
}

function Initialize-Frontend {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Die "npm not found on PATH. Install Node.js 20+, then re-run."
    }
    if (-not (Test-Path (Join-Path $Root 'frontend\node_modules'))) {
        Say 'frontend' 'installing node_modules (first run only, ~1 min)'
        Push-Location (Join-Path $Root 'frontend')
        try {
            npm install --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { Die "npm install failed." }
        } finally { Pop-Location }
    }
}

function Show-ProviderMode {
    $envFile = Join-Path $Root '.env'
    $hasKey = $false
    if (Test-Path $envFile) {
        if ((Get-Content $envFile -Raw) -match '(?m)^\s*GEMINI_API_KEY\s*=\s*\S+') { $hasKey = $true }
    }
    if ($hasKey) { Say 'provider' 'GEMINI_API_KEY present - hosted Gemma' }
    else { Say 'provider' 'no GEMINI_API_KEY - deterministic mock mode (app fully usable)' }
}

# ------------------------------------------------------------------------ modes

if ($Stop)   { Invoke-StopAll; exit 0 }
if ($Status) { Invoke-Status;  exit 0 }

if ($Test) {
    Head 'tests'
    $py = Initialize-Backend
    Initialize-Frontend
    Push-Location (Join-Path $Root 'backend')
    try { & $py -m pytest tests -q; $backendOk = ($LASTEXITCODE -eq 0) } finally { Pop-Location }
    Push-Location (Join-Path $Root 'frontend')
    try { npm run build; $frontendOk = ($LASTEXITCODE -eq 0) } finally { Pop-Location }
    Write-Host ""
    if ($backendOk) { Say 'backend tests' 'PASS' } else { Say 'backend tests' 'FAIL' }
    if ($frontendOk) { Say 'frontend build' 'PASS' } else { Say 'frontend build' 'FAIL' }
    if ($backendOk -and $frontendOk) { exit 0 }
    exit 1
}

# --------------------------------------------------------------------- start up

if ($Prod) { Head 'Lamer Konekte - starting (prod)' } else { Head 'Lamer Konekte - starting (dev)' }

$py = Initialize-Backend
Initialize-Frontend
Show-ProviderMode

$BackendPort = Resolve-UsablePort $BackendPort 'Backend'
if (-not $Prod) { $FrontendPort = Resolve-UsablePort $FrontendPort 'Frontend' }

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
$beOut = Join-Path $RunDir 'backend.log'
$beErr = Join-Path $RunDir 'backend.err.log'
$feOut = Join-Path $RunDir 'frontend.log'
$feErr = Join-Path $RunDir 'frontend.err.log'

if ($Prod) {
    Say 'frontend' 'building...'
    Push-Location (Join-Path $Root 'frontend')
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { Die "frontend build failed (see output above)." }
    } finally { Pop-Location }
    if (-not (Test-Path (Join-Path $Root 'frontend\dist\index.html'))) {
        Die "build produced no frontend/dist/index.html"
    }
    Say 'frontend' "built - served by the backend on :$BackendPort"
}

$beArgs = @('-m', 'uvicorn', 'app.main:app', '--host', $BindHost, '--port', "$BackendPort")
if (-not $Prod) { $beArgs += '--reload' }

$be = Start-Process -FilePath $py -ArgumentList $beArgs `
        -WorkingDirectory (Join-Path $Root 'backend') `
        -RedirectStandardOutput $beOut -RedirectStandardError $beErr `
        -WindowStyle Hidden -PassThru
Set-Content -Path (Join-Path $RunDir 'backend.pid') -Value $be.Id -Encoding utf8

if (Wait-Http "http://$BindHost`:$BackendPort/health" 60 @($beOut, $beErr)) {
    Say 'backend' "ready on http://$BindHost`:$BackendPort (pid $($be.Id))"
} else {
    Invoke-StopAll | Out-Null
    Die "backend did not become healthy within 60s. Logs: $beOut / $beErr"
}

if (-not $Prod) {
    # --host pins Vite to the interface we health-check. Without it Vite binds
    # "localhost", which resolves to ::1 first on Windows and then never answers
    # on 127.0.0.1 - the server is up but every check times out.
    $npmCmd = (Get-Command npm).Source
    if ($npmCmd -notmatch '\.(cmd|exe|bat)$') { $npmCmd = 'npm.cmd' }
    $feArgs = @('run', 'dev', '--', '--host', $BindHost, '--port', "$FrontendPort", '--strictPort')
    $fe = Start-Process -FilePath $npmCmd -ArgumentList $feArgs `
            -WorkingDirectory (Join-Path $Root 'frontend') `
            -RedirectStandardOutput $feOut -RedirectStandardError $feErr `
            -WindowStyle Hidden -PassThru
    Set-Content -Path (Join-Path $RunDir 'frontend.pid') -Value $fe.Id -Encoding utf8

    if (Wait-Http "http://$BindHost`:$FrontendPort/" 90 @($feOut, $feErr)) {
        Say 'frontend' "ready on http://$BindHost`:$FrontendPort (pid $($fe.Id))"
    } else {
        Invoke-StopAll | Out-Null
        Die "Vite did not start within 90s. Logs: $feOut / $feErr"
    }
}

if ($Prod) { $appUrl = "http://$BindHost`:$BackendPort" } else { $appUrl = "http://$BindHost`:$FrontendPort" }

Write-Host ""
Write-Host "  Open  $appUrl" -ForegroundColor Green
Say 'api docs' "http://$BindHost`:$BackendPort/docs"
if ($Prod) { Say 'mode' 'production - service worker active (offline/PWA testable)' }
else { Say 'mode' 'dev - hot reload; service worker only runs in -Prod' }
Say 'logs' $RunDir
Say 'stop' '.\run.ps1 -Stop'

if ($Audit) {
    Head 'design audit'
    Say 'checks' $AuditChecks
    if ($AuditChecks -notmatch 'contrast|scaling') {
        Say 'note' 'contrast + scaling are the slow sweeps: -AuditChecks contrast,scaling'
    }
    Push-Location (Join-Path $Root 'frontend')
    try { node scripts/design-audit.mjs --base=$appUrl --checks=$AuditChecks } finally { Pop-Location }
}

if (-not $NoBrowser) { Start-Process $appUrl }
