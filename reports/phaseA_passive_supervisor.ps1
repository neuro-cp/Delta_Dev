param($RunnerPid, $RepoRoot)
$ErrorActionPreference = 'Continue'
Set-Location $RepoRoot
$reports = Join-Path $RepoRoot 'reports'
$log = Join-Path $reports 'phaseA_passive_supervisor.log'
$python = Join-Path $RepoRoot '.venv311\Scripts\python.exe'
$campaignRoot = Join-Path $RepoRoot '.tmp\experiments\phaseA_architecture_graduation'
Add-Content $log "$(Get-Date -Format o) passive supervisor watching runner pid $RunnerPid"
while (Get-Process -Id $RunnerPid -ErrorAction SilentlyContinue) {
  Start-Sleep -Seconds 60
}
Add-Content $log "$(Get-Date -Format o) primary Phase A runner exited; launching overnight_3000"
$args = @(
  '-m', 'tools.phaseA_architecture_graduation',
  '--campaign-root', '.tmp\experiments\phaseA_architecture_graduation',
  '--reports-dir', 'reports',
  '--campaign', 'overnight_3000',
  '--ignore-prerequisites',
  '--reset'
)
$out = Join-Path $reports 'phaseA_overnight_3000.out.log'
$err = Join-Path $reports 'phaseA_overnight_3000.err.log'
$p = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $RepoRoot -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
Add-Content $log "$(Get-Date -Format o) overnight_3000 pid $($p.Id) started"
Wait-Process -Id $p.Id
Add-Content $log "$(Get-Date -Format o) overnight_3000 pid $($p.Id) exited with code $($p.ExitCode)"
if (-not (Test-Path (Join-Path $reports 'phaseA_complete.json'))) {
  $payload = [ordered]@{
    timestamp = (Get-Date).ToUniversalTime().ToString('o')
    success = $false
    final_stage = 'stage3_graduation'
    final_campaign = 'overnight_3000'
    final_campaign_status = 'unknown'
    stop_reason = 'phaseA_complete.json missing after overnight_3000 exit'
    conclusion = 'unknown'
    canonical_merge_performed = $false
    report_paths = [ordered]@{
      graduation = (Join-Path $reports 'PhaseA_Architecture_Graduation.md')
      summary = (Join-Path $reports 'phaseA_temp_store_validation_report.md')
      summary_json = (Join-Path $reports 'phaseA_temp_store_validation_report.json')
      promotion_stability = (Join-Path $reports 'phaseA_promotion_stability.md')
      dry_run = (Join-Path $reports 'phaseA_canonical_promotion_dry_run.md')
    }
  }
  $payload | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $reports 'phaseA_complete.json') -Encoding UTF8
  Add-Content $log "$(Get-Date -Format o) wrote fallback sentinel because normal sentinel was missing"
}
