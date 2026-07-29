<#
.SYNOPSIS
  Poll the E2B training kernel until it reaches a terminal state.
.DESCRIPTION
  Polls responsibly (default 60 s). On failure it captures the log so the error is
  recorded rather than lost.
.EXAMPLE
  pwsh scripts/kaggle_monitor_ai_training.ps1 -IntervalSeconds 60 -TimeoutMinutes 300
#>
param(
    [int]$IntervalSeconds = 60,
    [int]$TimeoutMinutes = 300
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$meta = Get-Content (Join-Path $repo "kaggle/notebooks/kernel-metadata.json") | ConvertFrom-Json
$kernel = $meta.id
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)

Write-Host "Monitoring $kernel (every ${IntervalSeconds}s, up to ${TimeoutMinutes}m)" -ForegroundColor Cyan
while ((Get-Date) -lt $deadline) {
    $status = (kaggle kernels status $kernel 2>&1) -join " "
    $stamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$stamp] $status"
    if ($status -match "complete") {
        Write-Host "Run COMPLETE." -ForegroundColor Green
        Write-Host "Download with: pwsh scripts/kaggle_download_ai_outputs.ps1"
        exit 0
    }
    if ($status -match "error|cancel") {
        Write-Host "Run FAILED. Capturing log..." -ForegroundColor Red
        $logDir = Join-Path $repo "training/results"
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        kaggle kernels output $kernel -p $logDir 2>&1 | Out-Null
        $logFile = Join-Path $logDir "kaggle_failure_log.txt"
        $status | Out-File -FilePath $logFile -Encoding utf8
        Write-Host "Status written to $logFile" -ForegroundColor Yellow
        exit 2
    }
    Start-Sleep -Seconds $IntervalSeconds
}
Write-Host "Timed out after $TimeoutMinutes minutes; the kernel may still be running." -ForegroundColor Yellow
exit 3
