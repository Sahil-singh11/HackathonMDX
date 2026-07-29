<#
.SYNOPSIS
  Resume the E2B training workflow after a blocker clears.
.DESCRIPTION
  Idempotent: re-validates the dataset, re-pushes it, re-pushes the notebook and
  monitors. Safe to run repeatedly.
.EXAMPLE
  pwsh scripts/kaggle_resume_ai_training.ps1
#>
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot

Write-Host "== 1/3 dataset ==" -ForegroundColor Cyan
& (Join-Path $here "kaggle_push_ai_dataset.ps1") -NewVersion -Message "resume run"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "== 2/3 notebook ==" -ForegroundColor Cyan
& (Join-Path $here "kaggle_push_ai_training.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "== 3/3 monitor ==" -ForegroundColor Cyan
& (Join-Path $here "kaggle_monitor_ai_training.ps1")
exit $LASTEXITCODE
