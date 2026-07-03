from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v16_env import DeltaEvaluatorEnv, load_delta_evaluator_env
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import (
    ExternalEvaluatorTrialStatus,
    run_external_evaluator_api_trial,
    validate_external_evaluator_api_trial_safe,
)


DEFAULT_RUN_LOG = Path("data/runtime_v16g/manual_evaluator_runs.jsonl")

RUNTIME_V16G_MANUAL_RUN_FLAGS: dict[str, bool] = {
    "manual_run_hardening_enabled": True,
    "dry_run_default": True,
    "scheduler_enabled": False,
    "background_worker_enabled": False,
    "api_call_performed_by_default": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class ManualEvaluatorRunDecisionValue(str, Enum):
    DRY_RUN_READY = "dry_run_ready"
    LIVE_ALLOWED = "live_allowed"
    LIVE_REFUSED = "live_refused"
    DUPLICATE_RUN_ID = "duplicate_run_id"


@dataclass(frozen=True)
class ManualEvaluatorRunRequest:
    run_id: str
    live: bool = False
    show_request: bool = False
    output_report: bool = False
    explicit_retry: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ManualEvaluatorRunLock:
    lock_id: str
    run_id: str
    run_log_path: str
    duplicate_run_id: bool
    background_worker_started: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ManualEvaluatorRunDecision:
    decision_id: str
    decision: ManualEvaluatorRunDecisionValue
    rationale: str
    applied: bool = False
    scheduler_started: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["decision"] = self.decision.value
        return data


@dataclass(frozen=True)
class ManualEvaluatorAuditRecord:
    audit_id: str
    run_id: str
    redacted_request_logged: bool
    provider_call_performed: bool
    advisory_only: bool = True
    no_memory_mutation: bool = True
    no_recall_mutation: bool = True
    no_training: bool = True
    no_action_execution: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_manual_evaluator_run_request(run_id: str = "", *, live: bool = False, show_request: bool = False, output_report: bool = False) -> ManualEvaluatorRunRequest:
    resolved_run_id = run_id or _stable_id("v16g-manual-run", "default-dry-run")
    return ManualEvaluatorRunRequest(run_id=resolved_run_id, live=live, show_request=show_request, output_report=output_report)


def run_hardened_manual_evaluator(
    request: ManualEvaluatorRunRequest | None = None,
    *,
    env: DeltaEvaluatorEnv | None = None,
    run_log_path: str | Path = DEFAULT_RUN_LOG,
    persist_run_log: bool = False,
) -> dict[str, object]:
    req = request or build_manual_evaluator_run_request()
    cfg = env or load_delta_evaluator_env()
    log_path = Path(run_log_path)
    duplicate = _run_id_exists(log_path, req.run_id)
    lock = ManualEvaluatorRunLock(
        lock_id=_stable_id("v16g-lock", req.run_id, log_path),
        run_id=req.run_id,
        run_log_path=str(log_path),
        duplicate_run_id=duplicate,
    )
    if duplicate:
        trial = run_external_evaluator_api_trial(cfg, live=False)
        decision = ManualEvaluatorRunDecision(
            decision_id=_stable_id("v16g-decision", req.run_id, "duplicate"),
            decision=ManualEvaluatorRunDecisionValue.DUPLICATE_RUN_ID,
            rationale="Run ID already exists; duplicate run blocked.",
        )
    else:
        trial = run_external_evaluator_api_trial(cfg, live=req.live)
        status = trial["trial_result"]["status"]
        if req.live and status == ExternalEvaluatorTrialStatus.LIVE_CALL_COMPLETED.value:
            decision_value = ManualEvaluatorRunDecisionValue.LIVE_ALLOWED
        elif req.live:
            decision_value = ManualEvaluatorRunDecisionValue.LIVE_REFUSED
        else:
            decision_value = ManualEvaluatorRunDecisionValue.DRY_RUN_READY
        decision = ManualEvaluatorRunDecision(
            decision_id=_stable_id("v16g-decision", req.run_id, decision_value.value),
            decision=decision_value,
            rationale="Manual evaluator run completed as advisory-only dry/live trial.",
        )
        if persist_run_log:
            _append_run_log(log_path, req.run_id, decision.decision.value)
    audit = ManualEvaluatorAuditRecord(
        audit_id=_stable_id("v16g-audit", req.run_id, decision.decision.value),
        run_id=req.run_id,
        redacted_request_logged=req.show_request or req.output_report,
        provider_call_performed=bool(trial["trial_result"]["provider_call_performed"]),
    )
    return {
        "phase": "Runtime V1.6G",
        "request": req.as_dict(),
        "lock": lock.as_dict(),
        "decision": decision.as_dict(),
        "trial": trial,
        "audit": audit.as_dict(),
        "invariant_flags": dict(RUNTIME_V16G_MANUAL_RUN_FLAGS),
        "final_recommendation": "PROCEED_REVIEW_UI_APPROVAL_REJECTION_EXPORT_FLOW",
    }


def validate_hardened_manual_evaluator_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    audit = payload["audit"]
    return (
        validate_external_evaluator_api_trial_safe(payload["trial"])
        and payload["decision"]["applied"] is False
        and payload["decision"]["scheduler_started"] is False
        and payload["lock"]["background_worker_started"] is False
        and audit["advisory_only"] is True
        and audit["no_memory_mutation"] is True
        and audit["no_recall_mutation"] is True
        and audit["no_training"] is True
        and audit["no_action_execution"] is True
        and flags["manual_run_hardening_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"manual_run_hardening_enabled", "dry_run_default"})
    )


def _run_id_exists(path: Path, run_id: str) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                if json.loads(line).get("run_id") == run_id:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def _append_run_log(path: Path, run_id: str, decision: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"run_id": run_id, "decision": decision}, sort_keys=True) + "\n")


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
