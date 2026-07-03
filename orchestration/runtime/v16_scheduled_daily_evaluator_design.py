from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v16_env import load_delta_evaluator_env, parse_env_file


RUNTIME_V16E_SCHEDULED_EVALUATOR_FLAGS: dict[str, bool] = {
    "scheduled_evaluator_design_enabled": True,
    "schedule_plan_only": True,
    "active_scheduler_enabled": False,
    "os_task_created": False,
    "cron_entry_created": False,
    "windows_scheduled_task_created": False,
    "api_call_performed": False,
    "automatic_daily_run_enabled": False,
    "background_worker_enabled": False,
    "timer_enabled": False,
    "queue_enabled": False,
    "training_enabled": False,
    "canonical_write_enabled": False,
    "memory_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "action_execution_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class DailyEvaluatorScheduleDecisionValue(str, Enum):
    DESIGN_ONLY_DISABLED = "design_only_disabled"
    FUTURE_GATES_PRESENT_BUT_NOT_ACTIVE = "future_gates_present_but_not_active"


@dataclass(frozen=True)
class DailyEvaluatorRunWindow:
    window_id: str
    cadence: str
    local_time: str
    timezone: str = "local"
    active: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorGateStatus:
    gate_status_id: str
    evaluator_enabled: bool
    live_call_allowed: bool
    api_key_present: bool
    future_scheduler_enabled: bool
    gates_satisfied_for_future_manual_review: bool
    active_scheduler_enabled: bool = False
    api_call_allowed_now: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorBatchSelectionPolicy:
    policy_id: str
    source_reports: tuple[str, ...]
    max_candidates: int = 10
    include_candidate_only: bool = True
    include_advisory_reviews: bool = True
    mutate_selection: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorLockfilePlan:
    lockfile_plan_id: str
    lockfile_path: str = ".tmp/delta_daily_evaluator.lock"
    create_lockfile_now: bool = False
    duplicate_run_prevention: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorFailurePolicy:
    failure_policy_id: str
    retry_count: int = 0
    fail_closed: bool = True
    write_error_report_only: bool = True
    escalate_to_manual_review: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorAuditPlan:
    audit_plan_id: str
    report_directory: str = "reports"
    append_only_report_names: bool = True
    include_redacted_env: bool = True
    include_no_authority_statement: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorManualRunCommand:
    command_id: str
    command_text: str
    text_only: bool = True
    executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorScheduleDecision:
    decision_id: str
    decision: DailyEvaluatorScheduleDecisionValue
    rationale: str
    applied: bool = False
    active_scheduler_enabled: bool = False
    api_call_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class DailyEvaluatorSchedulePlan:
    plan_id: str
    run_window: DailyEvaluatorRunWindow
    gate_status: DailyEvaluatorGateStatus
    batch_policy: DailyEvaluatorBatchSelectionPolicy
    lockfile_plan: DailyEvaluatorLockfilePlan
    failure_policy: DailyEvaluatorFailurePolicy
    audit_plan: DailyEvaluatorAuditPlan
    manual_run_command: DailyEvaluatorManualRunCommand
    decision: DailyEvaluatorScheduleDecision

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "run_window": self.run_window.as_dict(),
            "gate_status": self.gate_status.as_dict(),
            "batch_policy": self.batch_policy.as_dict(),
            "lockfile_plan": self.lockfile_plan.as_dict(),
            "failure_policy": self.failure_policy.as_dict(),
            "audit_plan": self.audit_plan.as_dict(),
            "manual_run_command": self.manual_run_command.as_dict(),
            "decision": self.decision.as_dict(),
        }


def build_scheduled_daily_evaluator_plan() -> DailyEvaluatorSchedulePlan:
    cfg = load_delta_evaluator_env()
    file_env = parse_env_file()
    schedule_enabled = _parse_bool(file_env.get("DELTA_EVALUATOR_SCHEDULE_ENABLED", "false"))
    cadence = file_env.get("DELTA_EVALUATOR_SCHEDULE_CADENCE", "daily") or "daily"
    local_time = file_env.get("DELTA_EVALUATOR_SCHEDULE_LOCAL_TIME", "03:00") or "03:00"
    dry_run = _parse_bool(file_env.get("DELTA_EVALUATOR_SCHEDULE_DRY_RUN", "true"))
    run_window = DailyEvaluatorRunWindow(
        window_id=_stable_id("v16e-run-window", cadence, local_time),
        cadence=cadence,
        local_time=local_time,
        active=False,
    )
    gate_status = DailyEvaluatorGateStatus(
        gate_status_id=_stable_id("v16e-gates", cfg.enabled, cfg.allow_live_call, cfg.api_key_present, schedule_enabled),
        evaluator_enabled=cfg.enabled,
        live_call_allowed=cfg.allow_live_call,
        api_key_present=cfg.api_key_present,
        future_scheduler_enabled=schedule_enabled,
        gates_satisfied_for_future_manual_review=cfg.enabled and cfg.allow_live_call and cfg.api_key_present and schedule_enabled,
    )
    batch_policy = DailyEvaluatorBatchSelectionPolicy(
        policy_id=_stable_id("v16e-batch-policy", "candidate-only", "advisory"),
        source_reports=(
            "reports/runtime_v16a_validated_experience_learning_loop.json",
            "reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.json",
        ),
    )
    lockfile_plan = DailyEvaluatorLockfilePlan(lockfile_plan_id=_stable_id("v16e-lockfile", ".tmp/delta_daily_evaluator.lock"))
    failure_policy = DailyEvaluatorFailurePolicy(failure_policy_id=_stable_id("v16e-failure", "fail-closed"))
    audit_plan = DailyEvaluatorAuditPlan(audit_plan_id=_stable_id("v16e-audit", "reports"))
    command_text = ".\\.venv311\\Scripts\\python.exe scripts\\run_delta_evaluator_trial.py --show-request"
    if not dry_run:
        command_text += " --live --output-report"
    manual_command = DailyEvaluatorManualRunCommand(
        command_id=_stable_id("v16e-manual-command", command_text),
        command_text=command_text,
    )
    decision_value = (
        DailyEvaluatorScheduleDecisionValue.FUTURE_GATES_PRESENT_BUT_NOT_ACTIVE
        if gate_status.gates_satisfied_for_future_manual_review
        else DailyEvaluatorScheduleDecisionValue.DESIGN_ONLY_DISABLED
    )
    decision = DailyEvaluatorScheduleDecision(
        decision_id=_stable_id("v16e-decision", decision_value.value),
        decision=decision_value,
        rationale="Schedule design is recorded, but no scheduler is activated and no API call is performed.",
    )
    return DailyEvaluatorSchedulePlan(
        plan_id=_stable_id("v16e-plan", run_window.window_id, gate_status.gate_status_id, manual_command.command_id),
        run_window=run_window,
        gate_status=gate_status,
        batch_policy=batch_policy,
        lockfile_plan=lockfile_plan,
        failure_policy=failure_policy,
        audit_plan=audit_plan,
        manual_run_command=manual_command,
        decision=decision,
    )


def validate_scheduled_daily_evaluator_plan_safe(plan: DailyEvaluatorSchedulePlan) -> bool:
    data = plan.as_dict()
    flags = RUNTIME_V16E_SCHEDULED_EVALUATOR_FLAGS
    return (
        data["run_window"]["active"] is False
        and data["gate_status"]["active_scheduler_enabled"] is False
        and data["gate_status"]["api_call_allowed_now"] is False
        and data["lockfile_plan"]["create_lockfile_now"] is False
        and data["manual_run_command"]["text_only"] is True
        and data["manual_run_command"]["executed"] is False
        and data["decision"]["applied"] is False
        and data["decision"]["active_scheduler_enabled"] is False
        and data["decision"]["api_call_performed"] is False
        and flags["scheduled_evaluator_design_enabled"] is True
        and flags["schedule_plan_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"scheduled_evaluator_design_enabled", "schedule_plan_only"})
    )


def _parse_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, tuple):
            values[key] = list(value)
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
