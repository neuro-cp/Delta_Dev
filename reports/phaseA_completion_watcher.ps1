param($RunnerPid, $RepoRoot)
$ErrorActionPreference = 'SilentlyContinue'
Set-Location $RepoRoot
$reports = Join-Path $RepoRoot 'reports'
$sentinel = Join-Path $reports 'phaseA_complete.json'
$log = Join-Path $reports 'phaseA_completion_watcher.log'
function Read-Json($path) {
  if (Test-Path $path) { return Get-Content $path -Raw | ConvertFrom-Json }
  return $null
}
function LatestCheckpoint($root) {
  $items = Get-ChildItem $root -Recurse -Filter phaseA_checkpoint.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
  if ($items.Count -gt 0) { return $items[0] }
  return $null
}
Add-Content $log "$(Get-Date -Format o) watching runner pid $RunnerPid"
while (Get-Process -Id $RunnerPid -ErrorAction SilentlyContinue) {
  Start-Sleep -Seconds 30
}
$campaignRoot = Join-Path $RepoRoot '.tmp\experiments\phaseA_architecture_graduation'
$summary = Read-Json (Join-Path $reports 'phaseA_temp_store_validation_report.json')
$latest = LatestCheckpoint $campaignRoot
$latestData = $null
if ($latest) { $latestData = Read-Json $latest.FullName }
$graduation = Join-Path $reports 'PhaseA_Architecture_Graduation.md'
$conclusion = 'unknown'
if (Test-Path $graduation) {
  $lines = Get-Content $graduation
  if ($lines.Count -gt 0) { $conclusion = $lines[-1] }
}
$payload = [ordered]@{
  timestamp = (Get-Date).ToUniversalTime().ToString('o')
  success = $false
  final_stage = $null
  final_campaign = $null
  final_campaign_status = $null
  stop_reason = $null
  conclusion = $conclusion
  canonical_merge_performed = $false
  report_paths = [ordered]@{
    graduation = $graduation
    summary = (Join-Path $reports 'phaseA_temp_store_validation_report.md')
    summary_json = (Join-Path $reports 'phaseA_temp_store_validation_report.json')
    promotion_stability = (Join-Path $reports 'phaseA_promotion_stability.md')
    dry_run = (Join-Path $reports 'phaseA_canonical_promotion_dry_run.md')
  }
}
if ($summary -and $summary.aggregate) {
  $agg = $summary.aggregate
  $payload.success = (($agg.blocking_stop_reasons.Count -eq 0) -and ($agg.completed_campaign_count -eq $agg.campaign_count))
  if ($agg.campaigns.Count -gt 0) {
    $last = $agg.campaigns[$agg.campaigns.Count - 1]
    $payload.final_stage = $last.stage
    $payload.final_campaign = $last.campaign
    $payload.final_campaign_status = $last.status
    $payload.stop_reason = $last.stop_reason
  }
} elseif ($latestData) {
  $payload.final_campaign_status = $latestData.status
  $payload.stop_reason = $latestData.stop_reason
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -Path $sentinel -Encoding UTF8
Add-Content $log "$(Get-Date -Format o) wrote $sentinel"
