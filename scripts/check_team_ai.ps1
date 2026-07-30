<#
.SYNOPSIS
    Verify hosted Gemma model connectivity and configuration. Changes nothing.

.DESCRIPTION
    Checks only what a teammate needs in order to use the production model:
    the backend is reachable, it reports hosted Gemma with the pinned model, real
    inference is on, the rejected E2B adapter is off, and no key is exposed.

    Prints a CHECK | RESULT | ACTION table and exits non-zero if anything required
    fails. It never prints a secret - keys are reported as present/absent only.

.PARAMETER Mode
    'shared' (Render) or 'local'. Omitted: inferred from frontend/.env.local.

.EXAMPLE
    .\scripts\check_team_ai.ps1
.EXAMPLE
    .\scripts\check_team_ai.ps1 -Mode shared
#>
[CmdletBinding()]
param(
    [ValidateSet('shared', 'local')][string]$Mode,
    [string]$BackendUrl,
    [int]$TimeoutSec = 90
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot

$MODEL = 'gemma-4-26b-a4b-it'
$SHARED_DEFAULT = 'https://lamer-konekte.onrender.com'
$LOCAL_DEFAULT = 'http://127.0.0.1:8000'

$rows = @()
$failed = 0

function Add-Row([string]$check, [bool]$ok, [string]$result, [string]$action = '', [bool]$required = $true) {
    if ($ok) { $verdict = 'PASS' } elseif ($required) { $verdict = 'FAIL' } else { $verdict = 'WARN' }
    if (-not $ok -and $required) { $script:failed++ }
    $script:rows += [pscustomobject]@{ CHECK = $check; RESULT = "$verdict  $result"; ACTION = $action }
}

# ------------------------------------------------------------------ resolve mode
$feEnv = Join-Path $Root 'frontend\.env.local'
$configuredBase = ''
if (Test-Path $feEnv) {
    foreach ($line in (Get-Content $feEnv)) {
        if ($line -match '^\s*VITE_API_BASE_URL\s*=\s*(\S*)\s*$') { $configuredBase = $Matches[1] }
    }
}
if (-not $Mode) {
    if ($configuredBase) { $Mode = 'shared' } else { $Mode = 'local' }
}
if (-not $BackendUrl) {
    if ($Mode -eq 'shared') {
        if ($configuredBase) { $BackendUrl = $configuredBase } else { $BackendUrl = $SHARED_DEFAULT }
    } else { $BackendUrl = $LOCAL_DEFAULT }
}
$BackendUrl = $BackendUrl.TrimEnd('/')

Write-Host ""
Write-Host "=== hosted Gemma configuration check ===" -ForegroundColor Cyan
Write-Host ("  mode           {0}" -f $Mode)
Write-Host ("  backend        {0}" -f $BackendUrl)
Write-Host ("  expected model {0}" -f $MODEL)
Write-Host ""

# ------------------------------------------------------------------ frontend config
if (Test-Path $feEnv) {
    if ($Mode -eq 'shared') {
        Add-Row 'frontend API base URL' ([bool]$configuredBase) `
            $(if ($configuredBase) { $configuredBase } else { 'empty' }) `
            $(if ($configuredBase) { '' } else { 'run configure_team_ai.ps1 -Mode shared' })
    } else {
        Add-Row 'frontend API base URL' ($configuredBase -eq '' -or $configuredBase -eq $LOCAL_DEFAULT) `
            $(if ($configuredBase) { $configuredBase } else { 'relative (dev proxy)' }) `
            $(if ($configuredBase -and $configuredBase -ne $LOCAL_DEFAULT) { 'clear VITE_API_BASE_URL for local mode' } else { '' })
    }
    # Inspect ASSIGNMENTS ONLY. The generated file deliberately CONTAINS the words
    # "NEVER put GEMINI_API_KEY in this file" as a warning, and a raw substring scan
    # flagged that comment as a leaked secret - a scanner that cries wolf on its own
    # safety notice stops being read. So: drop comments and blank values, then look for
    # a key-ish name actually being given a value.
    $assignments = @(Get-Content $feEnv | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' })
    $offenders = @($assignments | Where-Object { $_ -match '(?i)(GEMINI|API_?KEY|SECRET|TOKEN)\s*=\s*\S' })
    $feClean = ($offenders.Count -eq 0)
    Add-Row 'no secret in frontend env' $feClean `
        $(if ($feClean) { 'clean (assignments checked)' } else { 'SECRET ASSIGNED' }) `
        $(if ($feClean) { '' } else { 'REMOVE it: VITE_* is inlined into the public bundle' })
} else {
    # Absent is FATAL for shared mode (nothing points the frontend at Render) but merely
    # untidy for local mode: with no file the base is empty, which IS the local default.
    # Failing local mode here would send a correctly-working teammate chasing a non-problem.
    $required = ($Mode -eq 'shared')
    Add-Row 'frontend/.env.local' $false 'missing' `
        $(if ($required) { 'run .\scripts\configure_team_ai.ps1 -Mode shared' } `
          else { 'optional in local mode - the default is already relative' }) $required
}

# ------------------------------------------------------------------ local-only config
if ($Mode -eq 'local') {
    $envPath = Join-Path $Root '.env'
    $exists = Test-Path $envPath
    Add-Row 'backend .env exists' $exists $(if ($exists) { $envPath } else { 'missing' }) `
        $(if ($exists) { '' } else { 'copy .env.example to .env' })

    $hasKey = $false; $keyLen = 0; $pmode = ''; $pmodel = ''
    if ($exists) {
        foreach ($line in (Get-Content $envPath)) {
            if ($line -match '^\s*GEMINI_API_KEY\s*=\s*(\S+)\s*$') { $hasKey = $true; $keyLen = $Matches[1].Length }
            if ($line -match '^\s*PROVIDER_MODE\s*=\s*(\S+)') { $pmode = $Matches[1] }
            if ($line -match '^\s*GEMMA_MODEL\s*=\s*(\S+)') { $pmodel = $Matches[1] }
        }
    }
    # Value NEVER printed - only presence and length.
    Add-Row 'GEMINI_API_KEY configured' $hasKey `
        $(if ($hasKey) { "present ($keyLen chars, not printed)" } else { 'absent' }) `
        $(if ($hasKey) { '' } else { "add GEMINI_API_KEY=<authorised key> to $envPath" })

    Add-Row 'PROVIDER_MODE' ($pmode -eq 'hosted') $(if ($pmode) { $pmode } else { 'unset' }) `
        $(if ($pmode -eq 'hosted') { '' } else { 'set PROVIDER_MODE=hosted' })

    Add-Row 'GEMMA_MODEL' ($pmodel -eq $MODEL -or -not $pmodel) `
        $(if ($pmodel) { $pmodel } else { "unset (backend default $MODEL)" }) `
        $(if ($pmodel -and $pmodel -ne $MODEL) { "set GEMMA_MODEL=$MODEL" } else { '' })
}

# ------------------------------------------------------------------ backend reachability
$status = $null
try {
    Invoke-RestMethod -Uri "$BackendUrl/health" -TimeoutSec $TimeoutSec | Out-Null
    Add-Row 'backend reachable' $true "$BackendUrl/health"
    try {
        $status = Invoke-RestMethod -Uri "$BackendUrl/api/provider/status" -TimeoutSec $TimeoutSec
    } catch {
        Add-Row 'provider status' $false $_.Exception.Message 'check the backend log'
    }
} catch {
    $hint = if ($Mode -eq 'shared') {
        'Render sleeps when idle - retry once; first wake takes 30-60 s'
    } else { 'start it: .\run.ps1' }
    Add-Row 'backend reachable' $false 'no response' $hint
}

# ------------------------------------------------------------------ model + provider
if ($status) {
    $model = $status.hosted.model
    Add-Row 'model is the pinned production model' ($model -eq $MODEL) `
        $(if ($model) { $model } else { 'not reported' }) `
        $(if ($model -eq $MODEL) { '' } else { "expected $MODEL" })

    $configured = [bool]$status.hosted.configured
    Add-Row 'hosted Gemma configured' $configured `
        $(if ($configured) { 'yes' } else { 'no API key on that backend' }) `
        $(if ($configured) { '' } else { $(if ($Mode -eq 'shared') { 'ask the owner to set GEMINI_API_KEY in Render' } else { 'add the key to .env and restart' }) })

    $defaultMode = $status.default_mode
    Add-Row 'default provider mode' ($defaultMode -eq 'hosted') `
        $(if ($defaultMode) { $defaultMode } else { 'not reported' }) `
        $(if ($defaultMode -eq 'hosted') { '' } else { 'set PROVIDER_MODE=hosted' })

    $realInference = $false
    if ($status.capabilities -and $status.capabilities.hosted) {
        $realInference = [bool]$status.capabilities.hosted.real_inference
    }
    Add-Row 'real inference enabled' $realInference `
        $(if ($realInference) { 'true' } else { 'false' }) `
        $(if ($realInference) { '' } else { 'hosted provider is not active' })

    $localLoaded = [bool]$status.local.loaded
    Add-Row 'local Gemma weights NOT loaded' (-not $localLoaded) `
        $(if ($localLoaded) { 'loaded' } else { 'not loaded (correct)' }) `
        $(if ($localLoaded) { 'the production path is hosted; no weights are needed' } else { '' })

    # The rejected fine-tuned E2B adapter must not appear as a selectable provider.
    $json = ($status | ConvertTo-Json -Depth 8)
    $adapterOff = ($json -notmatch 'finetuned|e2b')
    Add-Row 'E2B adapter disabled' $adapterOff `
        $(if ($adapterOff) { 'not present as a provider' } else { 'REFERENCED' }) `
        $(if ($adapterOff) { '' } else { 'the rejected adapter must never be production' })

    # No key material may appear in the status payload.
    $noSecret = ($json -notmatch 'AIza[0-9A-Za-z_\-]{10,}') -and ($json -notmatch '(?i)"?(api_key|gemini_api_key)"?\s*[:=]\s*"[^"]{8,}')
    Add-Row 'no API key exposed by the API' $noSecret `
        $(if ($noSecret) { 'clean' } else { 'KEY-SHAPED STRING FOUND' }) `
        $(if ($noSecret) { '' } else { 'STOP and rotate the key' })
}

# ------------------------------------------------------------------ report
Write-Host ""
$rows | Format-Table -AutoSize -Property CHECK, RESULT, ACTION | Out-String -Width 200 | Write-Host

if ($failed -eq 0) {
    Write-Host "ALL CHECKS PASSED - hosted $MODEL is usable from this laptop." -ForegroundColor Green
    Write-Host "Open http://127.0.0.1:5173/proof once the frontend is running." -ForegroundColor Green
    Write-Host ""
    exit 0
}
Write-Host "$failed required check(s) failed - see the ACTION column." -ForegroundColor Red
Write-Host "Guide: docs\TEAM_AI_MODEL_SETUP.md" -ForegroundColor Red
Write-Host ""
exit 1
