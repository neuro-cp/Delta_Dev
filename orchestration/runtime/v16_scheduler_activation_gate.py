from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v16_env import load_delta_evaluator_env, parse_env_file


SCHEDULER_APPROVAL_TOKEN = "APPROVE_DAILY_EVALUATOR_SCHEDULE"

RUNTIME_V16F_SCHEDULER_GATE_FLAGS: dict[str, bool] = {
    "scheduler_activation_gate_enabled": True,
    "scheduler_started": False,
    "os_task_registered": False,
    "cron_entry_created": False,
    "windows_scheduled_task_created": False,
    "background_worker_started": False,
    "api_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class SchedulerActivationDecisionValue(str, Enum):
    REFUSED = "refused"
    DECISION_ONLY_ALLOWED = "decision_only_allowed"


@dataclass(frozen=True)
class SchedulerActivationRequest:
    request_id: str
    approval_text: str = ""
    dry_run_reviewed: bool = False
    lock_conflict: bool = False
    scheduler_already_running: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SchedulerActivationRequirement:
    name: str
    satisfied: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SchedulerActivationGateStatus:
    gate_status_id: str
    requirements: tuple[SchedulerActivationRequirement, ...]
    all_requirements_satisfied: bool
    scheduler_started: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "gate_status_id": self.gate_status_id,
            "requirements": [item.as_dict() for item in self.requirements],
            "all_requirements_satisfied": self.all_requirements_satisfied,
            "scheduler_started": self.scheduler_started,
        }


@dataclass(frozen=True)
class SchedulerActivationDecision:
    decision_id: str
    decision: SchedulerActivationDecisionValue
    rationale: str
    applied: bool = False
    scheduler_started: bool = False
    api_call_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["decision"] = self.decision.value
        return data


@dataclass(frozen=True)
class SchedulerActivationAuditRecord:
    audit_id: str
    request_id: str
    decision_id: str
    no_scheduler_started: bool = True
    no_os_task_registered: bool = True
    no_api_call_performed: bool = True
    no_memory_mutation: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_scheduler_activation_request(
    approval_text: str = "",
    *,
    dry_run_reviewed: bool = False,
    lock_conflict: bool = False,
    scheduler_already_running: bool = False,
) -> SchedulerActivationRequest:
    return SchedulerActivationRequest(
        request_id=_stable_id("v16f-scheduler-request", approval_text, dry_run_reviewed, lock_conflict, scheduler_already_running),
        approval_text=approval_text,
        dry_run_reviewed=dry_run_reviewed,
        lock_conflict=lock_conflict,
        scheduler_already_running=scheduler_already_running,
    )


def evaluate_scheduler_activation_gate(request: SchedulerActivationRequest | None = None) -> dict[str, object]:
    req = request or build_scheduler_activation_request()
    cfg = load_delta_evaluator_env()
    env = parse_env_file()
    schedule_enabled = _bool(os.environ.get("DELTA_EVALUATOR_SCHEDULE_ENABLED", env.get("DELTA_EVALUATOR_SCHEDULE_ENABLED")))
    requirements = (
        SchedulerActivationRequirement("DELTA_EVALUATOR_SCHEDULE_ENABLED=true", schedule_enabled, "future schedule env gate"),
        SchedulerActivationRequirement("DELTA_EVALUATOR_ENABLED=true", cfg.enabled, "evaluator env gate"),
        SchedulerActivationRequirement("DELTA_EVALUATOR_ALLOW_LIVE_CALL=true", cfg.allow_live_call, "live-call env gate"),
        SchedulerActivationRequirement("DELTA_EVALUATOR_API_KEY present", cfg.api_key_present, "redacted key presence only"),
        SchedulerActivationRequirement("explicit approval token", req.approval_text.strip() == SCHEDULER_APPROVAL_TOKEN, "strict scheduler approval token"),
        SchedulerActivationRequirement("dry_run reviewed", req.dry_run_reviewed, "dry run reviewed by operator"),
        SchedulerActivationRequirement("no lock conflict", not req.lock_conflict, "lock conflict absent"),
        SchedulerActivationRequirement("no active scheduler", not req.scheduler_already_running, "no scheduler already running"),
    )
    all_ok = all(item.satisfied for item in requirements)
    gate = SchedulerActivationGateStatus(
        gate_status_id=_stable_id("v16f-scheduler-gate", *(item.satisfied for item in requirements)),
        requirements=requirements,
        all_requirements_satisfied=all_ok,
    )
    decision = SchedulerActivationDecision(
        decision_id=_stable_id("v16f-scheduler-decision", gate.gate_status_id, all_ok),
        decision=SchedulerActivationDecisionValue.DECISION_ONLY_ALLOWED if all_ok else SchedulerActivationDecisionValue.REFUSED,
        rationale="All gates satisfied; decision only, no scheduler started." if all_ok else "One or more scheduler activation gates are not satisfied.",
    )
    audit = SchedulerActivationAuditRecord(
        audit_id=_stable_id("v16f-scheduler-audit", req.request_id, decision.decision_id),
        request_id=req.request_id,
        decision_id=decision.decision_id,
    )
    return {
        "phase": "Runtime V1.6F",
        "request": req.as_dict(),
        "gate_status": gate.as_dict(),
        "decision": decision.as_dict(),
        "audit": audit.as_dict(),
        "invariant_flags": dict(RUNTIME_V16F_SCHEDULER_GATE_FLAGS),
        "final_recommendation": "PROCEED_DAILY_EVALUATOR_MANUAL_RUN_HARDENING",
    }


def validate_scheduler_activation_gate_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    decision = payload["decision"]
    audit = payload["audit"]
    return (
        decision["applied"] is False
        and decision["scheduler_started"] is False
        and decision["api_call_performed"] is False
        and audit["no_scheduler_started"] is True
        and audit["no_os_task_registered"] is True
        and audit["no_api_call_performed"] is True
        and audit["no_memory_mutation"] is True
        and flags["scheduler_activation_gate_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "scheduler_activation_gate_enabled")
    )


def _bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
