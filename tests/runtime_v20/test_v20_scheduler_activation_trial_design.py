from __future__ import annotations

from orchestration.runtime.v20_scheduler_activation_trial_design import design_scheduler_activation_trial, validate_scheduler_activation_trial_design_safe
from orchestration.runtime.v20_scheduler_activation_trial_design_report import write_scheduler_activation_trial_design_report


def test_scheduler_design_disabled_by_default():
    payload = design_scheduler_activation_trial()
    assert payload["decision"]["disabled_by_default"] is True
    assert payload["decision"]["starts_scheduler_now"] is False


def test_no_os_task_or_cron_created():
    payload = design_scheduler_activation_trial()
    flags = payload["invariant_flags"]
    assert flags["windows_task_created"] is False
    assert flags["cron_created"] is False
    assert flags["background_worker_started"] is False


def test_approval_phrase_required():
    payload = design_scheduler_activation_trial()
    assert "APPROVE_DAILY_EVALUATOR_SCHEDULE" in payload["required_future_approval"]


def test_design_safe():
    assert validate_scheduler_activation_trial_design_safe(design_scheduler_activation_trial())


def test_report_generation():
    data = write_scheduler_activation_trial_design_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_V20_SAFETY_CHECKPOINT_REPORT"
