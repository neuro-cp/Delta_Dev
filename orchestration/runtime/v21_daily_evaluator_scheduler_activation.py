from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from orchestration.runtime.v16_env import parse_env_file
from orchestration.runtime.v20_scheduler_activation_trial_design import APPROVAL_TEXT


PLAN_PATH = Path("data/runtime_v21d/scheduler_activation_plan.json")
AUDIT_PATH = Path("data/runtime_v21d/scheduler_activation_audit.jsonl")
DISABLE_PLAN_PATH = Path("data/runtime_v21d/scheduler_disable_plan.json")

RUNTIME_V21D_FLAGS = {
    "daily_evaluator_scheduler_activation_trial_enabled": True,
    "disabled_by_default": True,
    "os_scheduler_task_created": False,
    "cron_entry_created": False,
    "background_worker_started": False,
    "api_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class SchedulerActivationPlan:
    plan_id: str
    cadence: str
    local_time: str
    dry_run: bool
    lockfile_policy: str = "refuse duplicate runs"
    failure_policy: str = "record advisory failure and stop"
    no_memory_mutation_policy: bool = True
    evaluator_results_advisory_only: bool = True
    os_task_registered: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_scheduler_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    required = _normalize(APPROVAL_TEXT)
    return {"approval_present": bool(normalized), "matches_required_shape": normalized == required}


def verify_scheduler_gates(env: dict[str, str] | None = None, approval_text: str = "") -> dict[str, object]:
    values = parse_env_file() if env is None else env
    approval = parse_scheduler_approval(approval_text)
    key = values.get("DELTA_EVALUATOR_API_KEY", "")
    return {
        "approval": approval,
        "env_enabled": values.get("DELTA_EVALUATOR_SCHEDULE_ENABLED", "").lower() == "true",
        "dry_run": values.get("DELTA_EVALUATOR_SCHEDULE_DRY_RUN", "true").lower() == "true",
        "api_key_present": bool(key and key != "put_key_here"),
        "key_redacted": True,
    }


def build_scheduler_activation_plan(env: dict[str, str] | None = None, *, dry_run: bool = True) -> dict[str, object]:
    values = parse_env_file() if env is None else env
    plan = SchedulerActivationPlan(
        _stable_id("v21d-plan", values.get("DELTA_EVALUATOR_SCHEDULE_CADENCE", "daily"), values.get("DELTA_EVALUATOR_SCHEDULE_LOCAL_TIME", "03:00"), dry_run),
        values.get("DELTA_EVALUATOR_SCHEDULE_CADENCE", "daily"),
        values.get("DELTA_EVALUATOR_SCHEDULE_LOCAL_TIME", "03:00"),
        dry_run,
    )
    return {
        "phase": "Runtime V2.1D",
        "plan": plan.as_dict(),
        "disable_plan": build_scheduler_disable_plan(),
        "invariant_flags": dict(RUNTIME_V21D_FLAGS),
        "final_recommendation": "PROCEED_HYB1_REEVALUATION_REPORT_ONLY",
    }


def activate_scheduler_local_artifact(approval_text: str, env: dict[str, str] | None = None, *, dry_run: bool = True) -> dict[str, object]:
    gates = verify_scheduler_gates(env, approval_text)
    plan_payload = build_scheduler_activation_plan(env, dry_run=dry_run)
    permitted = gates["approval"]["matches_required_shape"] and gates["env_enabled"] and (gates["dry_run"] or gates["api_key_present"])
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISABLE_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if permitted:
        PLAN_PATH.write_text(json.dumps(plan_payload["plan"], indent=2), encoding="utf-8")
        DISABLE_PLAN_PATH.write_text(json.dumps(plan_payload["disable_plan"], indent=2), encoding="utf-8")
        AUDIT_PATH.open("a", encoding="utf-8").write(json.dumps({"audit_id": _stable_id("v21d-audit", plan_payload["plan"]["plan_id"]), "local_artifact_created": True, "os_task_registered": False}, sort_keys=True) + "\n")
    return {
        **plan_payload,
        "gates": gates,
        "decision": {
            "permitted": permitted,
            "local_artifact_created": permitted,
            "os_task_registered": False,
            "background_worker_started": False,
        },
    }


def build_scheduler_disable_plan() -> dict[str, object]:
    return {
        "disable_plan_id": _stable_id("v21d-disable", "daily_evaluator"),
        "manual_disable_required": True,
        "removes_local_artifact_only": True,
        "os_task_disable_command_text_only": "No OS task is registered by this trial.",
    }


def validate_scheduler_activation_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    decision = payload.get("decision", {})
    return (
        decision.get("os_task_registered", False) is False
        and decision.get("background_worker_started", False) is False
        and flags["daily_evaluator_scheduler_activation_trial_enabled"] is True
        and flags["disabled_by_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"daily_evaluator_scheduler_activation_trial_enabled", "disabled_by_default"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
