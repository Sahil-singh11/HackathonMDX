# Repeat the resource check every N seconds (default 5). Ctrl-C to stop.
param([int]$IntervalSeconds = 5)
while ($true) {
  Clear-Host
  & "$PSScriptRoot\check_resources.ps1"
  Start-Sleep -Seconds $IntervalSeconds
}
