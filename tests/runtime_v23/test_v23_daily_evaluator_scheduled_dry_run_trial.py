from orchestration.runtime.v23_daily_evaluator_scheduled_dry_run_trial import APPROVAL_TEXT, run_scheduled_dry_run_trial, validate_scheduled_dry_run_safe
from orchestration.runtime.v23_daily_evaluator_scheduled_dry_run_trial_report import write_scheduled_dry_run_report


def test_disabled_by_default():
    payload = run_scheduled_dry_run_trial()
    assert payload["decision"]["permitted"] is False
    assert payload["decision"]["os_task_registered"] is False


def test_approval_required():
    payload = run_scheduled_dry_run_trial(approval_text="yes", env={"DELTA_DAILY_EVALUATOR_SCHEDULE_DRY_RUN_ENABLED": "true"})
    assert payload["decision"]["permitted"] is False


def test_dry_run_artifact_can_be_generated_without_os_task(tmp_path):
    payload = run_scheduled_dry_run_trial(approval_text=APPROVAL_TEXT, env={"DELTA_DAILY_EVALUATOR_SCHEDULE_DRY_RUN_ENABLED": "true"}, output_path=tmp_path / "plan.json", write_artifact=True)
    assert payload["decision"]["local_artifact_created"] is True
    assert payload["decision"]["os_task_registered"] is False
    assert payload["decision"]["cron_entry_created"] is False
    assert payload["decision"]["windows_task_created"] is False
    assert validate_scheduled_dry_run_safe(payload)


def test_no_mutation_training_action_or_hyb1_change():
    payload = run_scheduled_dry_run_trial()
    flags = payload["invariant_flags"]
    assert flags["api_call_performed"] is False
    assert flags["memory_write_performed"] is False
    assert flags["training_triggered"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_scheduled_dry_run_report()
    assert data["all_safe"] is True

