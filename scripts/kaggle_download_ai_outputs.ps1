<#
.SYNOPSIS
  Download E2B training outputs and verify adapter checksums.
.EXAMPLE
  pwsh scripts/kaggle_download_ai_outputs.ps1
#>
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$meta = Get-Content (Join-Path $repo "kaggle/notebooks/kernel-metadata.json") | ConvertFrom-Json
$dest = Join-Path $repo "kaggle/outputs/e2b_router"   # gitignored
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Write-Host "Downloading outputs for $($meta.id) ..." -ForegroundColor Cyan
kaggle kernels output $meta.id -p $dest
if ($LASTEXITCODE -ne 0) { Write-Host "download failed" -ForegroundColor Red; exit 1 }

Write-Host "== Files ==" -ForegroundColor Cyan
Get-ChildItem -Recurse $dest | Select-Object Name, Length | Format-Table

Write-Host "== SHA-256 ==" -ForegroundColor Cyan
$manifest = @{}
Get-ChildItem -Recurse -File $dest | ForEach-Object {
    $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    $manifest[$_.Name] = @{ sha256 = $h; bytes = $_.Length }
    Write-Host ("  {0,-40} {1}" -f $_.Name, $h.Substring(0, 16))
}
$results = Join-Path $repo "training/results"
New-Item -ItemType Directory -Force -Path $results | Out-Null
$manifest | ConvertTo-Json -Depth 4 | Out-File (Join-Path $results "adapter_checksums.json") -Encoding utf8

# Copy metric artifacts into the repo (small, reviewable); adapter weights stay gitignored.
foreach ($f in @("training_metrics.json", "evaluation_metrics.json", "training_history.csv",
                 "e2b_comparison.csv", "error_analysis.csv")) {
    $src = Get-ChildItem -Recurse -File $dest -Filter $f -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($src) { Copy-Item $src.FullName $results -Force; Write-Host "  copied $f -> training/results/" }
}
Write-Host "Done. Adapter weights remain in kaggle/outputs (gitignored)." -ForegroundColor Green
