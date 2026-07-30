<#
.SYNOPSIS
    Point this checkout at a hosted Gemma backend — shared (Render) or local.

.DESCRIPTION
    Gemma 4 26B (gemma-4-26b-a4b-it) runs on Google's servers through the official
    google-genai SDK. Nothing is downloaded and no GPU is used, so the only question
    is WHICH BACKEND this laptop's frontend talks to:

      1. Shared Render backend  - no API key needed on this laptop. The deployed
                                  backend holds the key and makes the Gemma calls.
      2. Local backend          - you run FastAPI too, so you need an authorised
                                  GEMINI_API_KEY in the repo-root .env (backend only).

    Writes frontend/.env.local (VITE_API_BASE_URL) and nothing else. It never writes,
    prints, or asks for a secret, and it never overwrites an existing repo-root .env.

.PARAMETER Mode
    'shared' or 'local'. Omit to be asked.

.PARAMETER BackendUrl
    Override the shared backend URL. Defaults to the team deployment.

.EXAMPLE
    .\scripts\configure_team_ai.ps1
.EXAMPLE
    .\scripts\configure_team_ai.ps1 -Mode shared
#>
[CmdletBinding()]
param(
    [ValidateSet('shared', 'local')][string]$Mode,
    [string]$BackendUrl = 'https://lamer-konekte.onrender.com'
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot

$MODEL = 'gemma-4-26b-a4b-it'
$LOCAL_URL = 'http://127.0.0.1:8000'

function Say([string]$k, [string]$v) { Write-Host ("  {0,-16} {1}" -f $k, $v) }
function Head([string]$t) { Write-Host ""; Write-Host "=== $t ===" -ForegroundColor Cyan }
function Warn([string]$m) { Write-Host "  ! $m" -ForegroundColor Yellow }
function Good([string]$m) { Write-Host "  $m" -ForegroundColor Green }

Head 'Lamer Konekte - team AI model access'
Say 'model' "$MODEL (hosted by Google; not downloaded)"
Say 'weights' 'none required'
Say 'GPU' 'none required'
Say 'internet' 'required'
Say 'E2B adapter' 'disabled (rejected by the acceptance gate; not production)'

# ------------------------------------------------------------------ choose a mode
if (-not $Mode) {
    Write-Host ""
    Write-Host "  Which backend should this laptop's frontend use?"
    Write-Host "    [1] Shared Render backend  - recommended, NO API key needed here"
    Write-Host "    [2] Local backend          - you run FastAPI; needs your own authorised key"
    Write-Host ""
    $choice = Read-Host "  Enter 1 or 2"
    switch ($choice.Trim()) {
        '1' { $Mode = 'shared' }
        '2' { $Mode = 'local' }
        default { Write-Host ""; Write-Host "ERROR: enter 1 or 2." -ForegroundColor Red; exit 1 }
    }
}

# ------------------------------------------------------------------ frontend env
$fePath = Join-Path $Root 'frontend\.env.local'
if ($Mode -eq 'shared') { $apiBase = $BackendUrl.TrimEnd('/') } else { $apiBase = '' }

$lines = @(
    '# Written by scripts/configure_team_ai.ps1. Safe to edit or delete.',
    '# NEVER put GEMINI_API_KEY in this file: Vite inlines VITE_* into the public bundle.',
    ''
)
if ($Mode -eq 'shared') {
    $lines += "# Shared Render backend. Hosted Gemma is called by the deployed backend."
    $lines += "VITE_API_BASE_URL=$apiBase"
} else {
    $lines += "# Local backend on $LOCAL_URL. Empty value keeps requests relative so"
    $lines += "# Vite's dev proxy forwards /api and /health to the local FastAPI server."
    $lines += "VITE_API_BASE_URL="
}
Set-Content -Path $fePath -Value $lines -Encoding utf8

Head 'frontend'
Say 'wrote' $fePath
if ($Mode -eq 'shared') { Say 'API base' $apiBase } else { Say 'API base' "(relative -> dev proxy -> $LOCAL_URL)" }
Say 'secret in it' 'none - by design'

# ------------------------------------------------------------------ per-mode backend
if ($Mode -eq 'shared') {
    Head 'shared Render backend'
    Good "Hosted Gemma is executed BY THE SHARED BACKEND, not on this laptop."
    Say 'your API key' 'not needed on this machine'
    Say 'key location' 'Render environment variables only'
    Say 'you run' 'the frontend only'

    Write-Host ""
    Write-Host "  Reachability check (no secret is sent or printed):"
    try {
        $health = Invoke-RestMethod -Uri "$apiBase/health" -TimeoutSec 90
        Good "  backend reachable - $apiBase/health"
        try {
            $st = Invoke-RestMethod -Uri "$apiBase/api/provider/status" -TimeoutSec 60
            $remoteModel = $st.hosted.model
            if ($remoteModel -eq $MODEL) { Good "  model confirmed - $remoteModel" }
            else { Warn "  backend reports model '$remoteModel' (expected $MODEL)" }
            if ($st.hosted.configured) { Good "  hosted Gemma configured on the backend" }
            else { Warn "  the shared backend has no API key configured - ask the owner" }
        } catch { Warn "  provider status unavailable: $($_.Exception.Message)" }
    } catch {
        Warn "  not reachable yet: $($_.Exception.Message)"
        Warn "  Render free tier sleeps when idle; the first request can take 30-60 s."
        Warn "  Re-run: .\scripts\check_team_ai.ps1 -Mode shared"
    }
} else {
    Head 'local backend'
    $envPath = Join-Path $Root '.env'
    $examplePath = Join-Path $Root '.env.example'

    if (Test-Path $envPath) {
        Good "  .env already exists - left untouched (your configuration is preserved)"
    } else {
        if (Test-Path $examplePath) {
            Copy-Item $examplePath $envPath
            Good "  created .env from .env.example (placeholders only, no key)"
        } else {
            Warn "  .env.example is missing; cannot create .env"
        }
    }

    # Detect WITHOUT printing. Only ever reports present/absent and a length.
    $hasKey = $false; $keyLen = 0; $modeLine = ''; $modelLine = ''
    if (Test-Path $envPath) {
        foreach ($line in (Get-Content $envPath)) {
            if ($line -match '^\s*GEMINI_API_KEY\s*=\s*(\S+)\s*$') { $hasKey = $true; $keyLen = $Matches[1].Length }
            if ($line -match '^\s*PROVIDER_MODE\s*=\s*(\S+)') { $modeLine = $Matches[1] }
            if ($line -match '^\s*GEMMA_MODEL\s*=\s*(\S+)') { $modelLine = $Matches[1] }
        }
    }

    if ($hasKey) { Good "  GEMINI_API_KEY is configured ($keyLen characters, value never printed)" }
    else {
        Warn "  GEMINI_API_KEY is NOT set."
        Write-Host ""
        Write-Host "  Add your authorised key here:" -ForegroundColor Yellow
        Write-Host "    file: $envPath"
        Write-Host "    line: GEMINI_API_KEY=<your authorised key>"
        Write-Host ""
        Write-Host "  Get a key from Google AI Studio (https://aistudio.google.com/apikey),"
        Write-Host "  or ask the project owner to share one SECURELY - never over ordinary chat."
        Write-Host "  Without a key the app still runs, in clearly disclosed mock mode."
    }

    if ($modelLine -eq $MODEL) { Good "  GEMMA_MODEL=$modelLine" }
    elseif ($modelLine) { Warn "  GEMMA_MODEL=$modelLine (expected $MODEL)" }
    else { Warn "  GEMMA_MODEL not set; backend default is $MODEL" }

    if ($modeLine -eq 'hosted') { Good "  PROVIDER_MODE=hosted" }
    elseif ($modeLine) { Warn "  PROVIDER_MODE=$modeLine (set it to 'hosted' for the real model)" }
    else { Warn "  PROVIDER_MODE not set; set it to 'hosted'" }

    Say 'key stays' 'backend-only - the frontend never receives it'
    Say 'you run' 'backend AND frontend'
}

# ------------------------------------------------------------------ what next
Head 'next'
if ($Mode -eq 'shared') {
    Write-Host "  cd `"$Root\frontend`""
    Write-Host "  npm install"
    Write-Host "  npm run dev"
    Write-Host ""
    Write-Host "  Then open http://127.0.0.1:5173/proof and confirm:"
} else {
    Write-Host "  cd `"$Root`""
    Write-Host "  .\run.ps1"
    Write-Host ""
    Write-Host "  Then open http://127.0.0.1:5173/proof and confirm:"
}
Say '' "Hosted Gemma: configured"
Say '' "model: $MODEL"
Say '' "Local Gemma (edge): not loaded"
Write-Host ""
Say 'verify' ".\scripts\check_team_ai.ps1 -Mode $Mode"
Say 'guide' 'docs\TEAM_AI_MODEL_SETUP.md'
Write-Host ""
