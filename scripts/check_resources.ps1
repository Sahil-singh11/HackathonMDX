# One-shot resource report (Windows host). No secrets, no device IDs.
Write-Host "=== Lamer Konekte resource check — $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="

Write-Host "--- RAM ---"
$os = Get-CimInstance Win32_OperatingSystem
$freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
Write-Host ("Available RAM: {0} GB of {1} GB" -f $freeGB, $totalGB)

Write-Host "--- CPU ---"
$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
Write-Host ("CPU load: {0}%" -f $cpu)

Write-Host "--- Disk (C:) ---"
$d = Get-PSDrive C
Write-Host ("Free: {0} GB / Used: {1} GB" -f [math]::Round($d.Free/1GB,1), [math]::Round($d.Used/1GB,1))

Write-Host "--- NVIDIA GPU / VRAM ---"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader
} else {
  Write-Host "nvidia-smi not available"
}

Write-Host "--- Python processes ---"
Get-Process python*, py* -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, @{n='RSS_MB';e={[math]::Round($_.WorkingSet64/1MB)}} -AutoSize

Write-Host "--- Node processes ---"
Get-Process node -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, @{n='RSS_MB';e={[math]::Round($_.WorkingSet64/1MB)}} -AutoSize

Write-Host "--- Model-related processes ---"
Get-Process | Where-Object { $_.ProcessName -match 'llama|ollama|lmstudio|uvicorn' } |
  Format-Table Id, ProcessName, @{n='RSS_MB';e={[math]::Round($_.WorkingSet64/1MB)}} -AutoSize
