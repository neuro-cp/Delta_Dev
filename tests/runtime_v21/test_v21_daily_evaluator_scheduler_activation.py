from __future__ import annotations

from orchestration.runtime.v20_scheduler_activation_trial_design import APPROVAL_TEXT
from orchestration.runtime.v21_daily_evaluator_scheduler_activation import (
    activate_scheduler_local_artifact,
    build_scheduler_activation_plan,
    build_scheduler_disable_plan,
    parse_scheduler_approval,
    validate_scheduler_activation_safe,
    verify_scheduler_gates,
)
from orchestration.runtime.v21_daily_evaluator_scheduler_activation_report import write_scheduler_activation_report


def _env() -> dict[str, str]:
    return {
        "DELTA_EVALUATOR_SCHEDULE_ENABLED": "true",
        "DELTA_EVALUATOR_SCHEDULE_CADENCE": "daily",
        "DELTA_EVALUATOR_SCHEDULE_LOCAL_TIME": "03:00",
        "DELTA_EVALUATOR_SCHEDULE_DRY_RUN": "true",
        "DELTA_EVALUATOR_API_KEY": "test-key",
    }


def test_disabled_design_by_default():
    payload = build_scheduler_activation_plan()
    assert payload["plan"]["os_task_registered"] is False
    assert validate_scheduler_activation_safe({**payload, "decision": {"os_task_registered": False, "background_worker_started": False}})


def test_exact_approval_required():
    assert parse_scheduler_approval("yes")["matches_required_shape"] is False
    assert parse_scheduler_approval(APPROVAL_TEXT)["matches_required_shape"] is True


def test_env_gates_required():
    gates = verify_scheduler_gates({}, APPROVAL_TEXT)
    assert gates["env_enabled"] is False


def test_local_artifact_activation_never_registers_os_task():
    payload = activate_scheduler_local_artifact(APPROVAL_TEXT, _env(), dry_run=True)
    assert payload["decision"]["local_artifact_created"] is True
    assert payload["decision"]["os_task_registered"] is False
    assert payload["decision"]["background_worker_started"] is False


def test_disable_plan_exists():
    plan = build_scheduler_disable_plan()
    assert plan["manual_disable_required"] is True


def test_report_generation():
    data = write_scheduler_activation_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_HYB1_REEVALUATION_REPORT_ONLY"
