<#
.SYNOPSIS
  One-command final AI verification (Windows).
.EXAMPLE
  pwsh scripts/run_final_ai_check.ps1              # offline
  pwsh scripts/run_final_ai_check.ps1 -Live        # + real hosted gates + Render
  pwsh scripts/run_final_ai_check.ps1 -Quick       # minimum demo readiness
#>
param([switch]$Live, [switch]$Quick)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repo "backend/.venv/Scripts/python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$mode = if ($Live) { "--live" } elseif ($Quick) { "--quick" } else { "--offline" }
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
& $py (Join-Path $repo "scripts/final_ai_check.py") $mode
exit $LASTEXITCODE
