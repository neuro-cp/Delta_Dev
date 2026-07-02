param($RunnerPid, $Root)
$ErrorActionPreference = 'SilentlyContinue'
function Read-Json($path) {
  if (Test-Path $path) { return Get-Content $path -Raw | ConvertFrom-Json }
  return $null
}
$alt = Join-Path $Root 'alternating_curriculum_1000\phaseA_checkpoint.json'
$stab = Join-Path $Root 'stability_1000\phaseA_checkpoint.json'
$overnight = Join-Path $Root 'overnight_2000\phaseA_checkpoint.json'
$log = Join-Path (Resolve-Path 'reports') 'phaseA_stage2_stop_watcher.log'
while ($true) {
  Start-Sleep -Seconds 2
  $proc = Get-Process -Id $RunnerPid -ErrorAction SilentlyContinue
  if (-not $proc) { Add-Content $log "$(Get-Date -Format o) runner already stopped"; break }
  $overnightCheckpoint = Read-Json $overnight
  if ($overnightCheckpoint) {
    Stop-Process -Id $RunnerPid -Force
    Add-Content $log "$(Get-Date -Format o) stopped runner because overnight_2000 started"
    break
  }
  $altCheckpoint = Read-Json $alt
  if ($altCheckpoint -and ($altCheckpoint.status -eq 'completed' -or $altCheckpoint.status -eq 'stopped')) {
    Stop-Process -Id $RunnerPid -Force
    Add-Content $log "$(Get-Date -Format o) stopped runner after alternating_curriculum_1000 status=$($altCheckpoint.status)"
    break
  }
  $stabCheckpoint = Read-Json $stab
  if ($stabCheckpoint -and $stabCheckpoint.status -eq 'stopped') {
    Stop-Process -Id $RunnerPid -Force
    Add-Content $log "$(Get-Date -Format o) stopped runner because stability_1000 stopped"
    break
  }
}
