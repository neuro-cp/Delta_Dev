from __future__ import annotations

import hashlib
from dataclasses import dataclass


APPROVAL_TEXT = "APPROVE_DAILY_EVALUATOR_SCHEDULE\napproved_by=user\nschedule_scope=daily_evaluator_only\nactivation_mode=manual_user_enabled"

RUNTIME_V20G_FLAGS = {
    "scheduler_activation_trial_design_enabled": True,
    "scheduler_started": False,
    "windows_task_created": False,
    "cron_created": False,
    "background_worker_started": False,
    "api_call_performed": False,
    "memory_write_performed": False,
    "training_triggered": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class SchedulerActivationTrialDecision:
    decision_id: str
    disabled_by_default: bool = True
    approval_required: bool = True
    windows_task_plan_text_only: bool = True
    cron_plan_text_only: bool = True
    rollback_plan_present: bool = True
    starts_scheduler_now: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def design_scheduler_activation_trial() -> dict[str, object]:
    decision = SchedulerActivationTrialDecision(_stable_id("v20g-decision", APPROVAL_TEXT))
    return {
        "phase": "Runtime V2.0G",
        "required_future_approval": APPROVAL_TEXT,
        "command_plan": {
            "windows_task_scheduler": "Text-only future plan; no task is registered.",
            "cron": "Text-only future plan; no cron entry is written.",
            "manual_disable": "Future disable command must be explicit and audited.",
            "lockfile_policy": "Future scheduler must refuse duplicate runs.",
            "dry_run_policy": "Future scheduler defaults to dry-run.",
        },
        "decision": decision.as_dict(),
        "invariant_flags": dict(RUNTIME_V20G_FLAGS),
        "final_recommendation": "PROCEED_V20_SAFETY_CHECKPOINT_REPORT",
    }


def validate_scheduler_activation_trial_design_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["starts_scheduler_now"] is False
        and flags["scheduler_activation_trial_design_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "scheduler_activation_trial_design_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
