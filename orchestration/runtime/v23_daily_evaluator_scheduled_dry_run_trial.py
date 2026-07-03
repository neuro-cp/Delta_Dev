from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


APPROVAL_TEXT = "APPROVE_DAILY_EVALUATOR_SCHEDULE_DRY_RUN\napproved_by=user\nschedule_scope=daily_evaluator_dry_run_only"

RUNTIME_V23E_FLAGS = {
    "daily_evaluator_scheduled_dry_run_trial_enabled": True,
    "disabled_by_default": True,
    "os_scheduler_task_created": False,
    "cron_entry_created": False,
    "windows_task_created": False,
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
class ScheduledDryRunRequest:
    request_id: str
    cadence: str = "daily"
    local_time: str = "03:00"

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_scheduled_dry_run_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    return {"approval_present": bool(normalized), "matches_required_shape": normalized == _normalize(APPROVAL_TEXT)}


def run_scheduled_dry_run_trial(
    *,
    approval_text: str = "",
    env: dict[str, str] | None = None,
    output_path: str | Path = Path("data/runtime_v23e/daily_evaluator_dry_run_plan.json"),
    write_artifact: bool = False,
) -> dict[str, object]:
    env_values = env or {}
    approval = parse_scheduled_dry_run_approval(approval_text)
    gate = {
        "approval": approval,
        "env_enabled": str(env_values.get("DELTA_DAILY_EVALUATOR_SCHEDULE_DRY_RUN_ENABLED", "")).lower() == "true",
    }
    permitted = gate["approval"]["matches_required_shape"] and gate["env_enabled"]
    request = ScheduledDryRunRequest(_stable_id("v23e-request", "daily", "03:00"))
    plan = {
        "plan_id": _stable_id("v23e-plan", request.request_id),
        "cadence": request.cadence,
        "local_time": request.local_time,
        "dry_run_only": True,
        "command": "python scripts/delta_scheduler_dry_run.py --dry-run",
        "next_run_utc": (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat(),
        "lockfile_policy": "refuse duplicate dry-run artifact",
        "disable_plan": "delete local dry-run artifact only; no OS task exists",
    }
    artifact_created = False
    if permitted and write_artifact:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        artifact_created = True
    return {
        "phase": "Runtime V2.3E",
        "request": request.as_dict(),
        "gate": gate,
        "plan": plan,
        "decision": {
            "permitted": permitted,
            "local_artifact_created": artifact_created,
            "os_task_registered": False,
            "cron_entry_created": False,
            "windows_task_created": False,
            "background_worker_started": False,
            "api_call_performed": False,
        },
        "invariant_flags": dict(RUNTIME_V23E_FLAGS),
        "final_recommendation": "PROCEED_V23_SAFETY_CHECKPOINT",
    }


def validate_scheduled_dry_run_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["os_task_registered"] is False
        and payload["decision"]["cron_entry_created"] is False
        and payload["decision"]["windows_task_created"] is False
        and payload["decision"]["background_worker_started"] is False
        and flags["daily_evaluator_scheduled_dry_run_trial_enabled"] is True
        and flags["disabled_by_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"daily_evaluator_scheduled_dry_run_trial_enabled", "disabled_by_default"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

