<#
.SYNOPSIS
  Validate and push the Lamer Konekte AI Instructions v1 dataset to Kaggle (private).

.DESCRIPTION
  Runs every dataset validator first. A failing leakage check BLOCKS the upload — a
  contaminated dataset must never reach a training run.

  Credentials come from ~/.kaggle/kaggle.json. No secret is printed.

.EXAMPLE
  pwsh scripts/kaggle_push_ai_dataset.ps1
  pwsh scripts/kaggle_push_ai_dataset.ps1 -NewVersion -Message "reviewed Morisyen batch 1"
#>
param(
    [switch]$NewVersion,
    [string]$Message = "Lamer Konekte AI Instructions v1"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repo "backend/.venv/Scripts/python.exe"
$stage = Join-Path $repo "kaggle/datasets/lamer-konekte-ai-training-v1"

if (-not (Test-Path "$HOME/.kaggle/kaggle.json")) {
    Write-Host "Kaggle credentials not found." -ForegroundColor Yellow
    Write-Host "Create an API token at https://www.kaggle.com/settings -> API -> Create New Token"
    Write-Host "then save the downloaded kaggle.json to: $HOME/.kaggle/kaggle.json"
    Write-Host "Do NOT paste the key into a chat or commit it."
    exit 1
}

Write-Host "== Validating dataset ==" -ForegroundColor Cyan
foreach ($check in @("validate_training_dataset", "check_training_leakage",
                     "check_semantic_family_split", "check_tool_arguments",
                     "check_training_safety")) {
    Write-Host ("  {0,-32}" -f $check) -NoNewline
    & $py (Join-Path $repo "scripts/$check.py") | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL" -ForegroundColor Red
        Write-Host "Upload blocked: $check failed. Fix the DATA, never the check." -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS" -ForegroundColor Green
}

Write-Host "== Staging files ==" -ForegroundColor Cyan
foreach ($f in @("master_records.jsonl", "train.jsonl", "validation.jsonl", "test.jsonl",
                 "external_test_manifest.json", "dataset_statistics.json")) {
    Copy-Item (Join-Path $repo "training/data/$f") $stage -Force
    Write-Host "  staged $f"
}
# The immutable external benchmark travels with the dataset so the notebook can score it.
Copy-Item (Join-Path $repo "evaluation/cases/morisyen_cases.json") $stage -Force
Write-Host "  staged morisyen_cases.json (immutable external test)"
Copy-Item (Join-Path $repo "training/configs/compact_router_v1.json") $stage -Force
Write-Host "  staged compact_router_v1.json (frozen prompt)"

Write-Host "== Uploading to Kaggle (private) ==" -ForegroundColor Cyan
Push-Location $stage
try {
    if ($NewVersion) {
        kaggle datasets version -m $Message -d
    } else {
        kaggle datasets create -p . --dir-mode zip
        if ($LASTEXITCODE -ne 0) {
            Write-Host "create failed (dataset may already exist); trying a new version" -ForegroundColor Yellow
            kaggle datasets version -m $Message -d
        }
    }
} finally {
    Pop-Location
}

if ($LASTEXITCODE -ne 0) { Write-Host "Upload failed." -ForegroundColor Red; exit 1 }
Write-Host "Dataset pushed." -ForegroundColor Green
