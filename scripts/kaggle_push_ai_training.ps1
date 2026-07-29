<#
.SYNOPSIS
  Push and launch the E2B QLoRA router notebook on Kaggle with GPU.
.DESCRIPTION
  Rebuilds the notebook from source cells, verifies it parses, then pushes it.
  Kaggle starts the kernel automatically on push. No secret is printed.
.EXAMPLE
  pwsh scripts/kaggle_push_ai_training.ps1
#>
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repo "backend/.venv/Scripts/python.exe"
$nbdir = Join-Path $repo "kaggle/notebooks"

if (-not (Test-Path "$HOME/.kaggle/kaggle.json")) {
    Write-Host "Kaggle credentials not found at $HOME/.kaggle/kaggle.json" -ForegroundColor Yellow
    Write-Host "https://www.kaggle.com/settings -> API -> Create New Token"
    exit 1
}

Write-Host "== Rebuilding notebook from source cells ==" -ForegroundColor Cyan
& $py (Join-Path $repo "kaggle/build_e2b_notebook.py")
if ($LASTEXITCODE -ne 0) { Write-Host "notebook build failed" -ForegroundColor Red; exit 1 }

Write-Host "== Verifying every code cell parses ==" -ForegroundColor Cyan
& $py -c @"
import ast, json, sys
nb = json.load(open(r'$nbdir/train_lamer_konekte_e2b_qlora.ipynb', encoding='utf-8'))
bad = 0
for i, c in enumerate(nb['cells']):
    if c['cell_type'] != 'code':
        continue
    try:
        ast.parse(''.join(c['source']))
    except SyntaxError as e:
        bad += 1
        print(f'cell {i}: {e.msg} (line {e.lineno})')
sys.exit(1 if bad else 0)
"@
if ($LASTEXITCODE -ne 0) { Write-Host "notebook has syntax errors" -ForegroundColor Red; exit 1 }

Write-Host "== Pushing notebook (GPU enabled) ==" -ForegroundColor Cyan
Push-Location $nbdir
try { kaggle kernels push -p . } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { Write-Host "push failed" -ForegroundColor Red; exit 1 }

$meta = Get-Content (Join-Path $nbdir "kernel-metadata.json") | ConvertFrom-Json
Write-Host "Pushed and queued: https://www.kaggle.com/code/$($meta.id)" -ForegroundColor Green
Write-Host "Monitor with: pwsh scripts/kaggle_monitor_ai_training.ps1"
