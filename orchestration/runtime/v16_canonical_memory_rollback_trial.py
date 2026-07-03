from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


ROLLBACK_HEADER = "ROLLBACK_CANONICAL_MEMORY_TRIAL"
ROLLBACK_APPROVED_BY = "approved_by=user"
ROLLBACK_SCOPE = "rollback_scope=single_trial_record_only"
DEFAULT_ROLLBACK_MARKERS = Path("data/runtime_v16j/canonical_trial_rollback_markers.jsonl")

RUNTIME_V16J_ROLLBACK_FLAGS: dict[str, bool] = {
    "canonical_trial_rollback_enabled": True,
    "dry_run_default": True,
    "broad_delete_enabled": False,
    "source_record_deleted": False,
    "provider_call_performed": False,
    "tool_call_performed": False,
    "action_execution_performed": False,
    "training_triggered": False,
    "recall_mutated": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class RollbackDecisionValue(str, Enum):
    DRY_RUN_ONLY = "dry_run_only"
    REJECTED_APPROVAL_MISSING = "rejected_approval_missing"
    REJECTED_APPROVAL_MISMATCH = "rejected_approval_mismatch"
    MARKER_WRITTEN = "marker_written"


@dataclass(frozen=True)
class CanonicalMemoryRollbackRequest:
    request_id: str
    canonical_record_id: str
    approval_text: str = ""
    dry_run: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalMemoryRollbackDecision:
    decision_id: str
    canonical_record_id: str
    decision: RollbackDecisionValue
    marker_written: bool = False
    source_record_deleted: bool = False
    broad_mutation: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["decision"] = self.decision.value
        return data


@dataclass(frozen=True)
class CanonicalMemoryRollbackAuditRecord:
    audit_id: str
    canonical_record_id: str
    rollback_marker_path: str
    original_record_preserved: bool = True
    provider_calls_performed: bool = False
    training_triggered: bool = False
    recall_mutated: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_rollback_approval_text(canonical_record_id: str) -> str:
    return "\n".join((ROLLBACK_HEADER, f"canonical_record_id={canonical_record_id}", ROLLBACK_APPROVED_BY, ROLLBACK_SCOPE))


def execute_canonical_memory_rollback_trial(
    canonical_record_id: str,
    approval_text: str = "",
    *,
    dry_run: bool = True,
    marker_path: str | Path = DEFAULT_ROLLBACK_MARKERS,
) -> dict[str, object]:
    request = CanonicalMemoryRollbackRequest(_stable_id("v16j-rollback-request", canonical_record_id, approval_text, dry_run), canonical_record_id, approval_text, dry_run)
    marker_file = Path(marker_path)
    if dry_run:
        decision_value = RollbackDecisionValue.DRY_RUN_ONLY
        marker_written = False
    elif not approval_text.strip():
        decision_value = RollbackDecisionValue.REJECTED_APPROVAL_MISSING
        marker_written = False
    elif _normalize(approval_text) != _normalize(build_rollback_approval_text(canonical_record_id)):
        decision_value = RollbackDecisionValue.REJECTED_APPROVAL_MISMATCH
        marker_written = False
    else:
        decision_value = RollbackDecisionValue.MARKER_WRITTEN
        marker_written = True
        _write_marker(marker_file, canonical_record_id)
    decision = CanonicalMemoryRollbackDecision(
        decision_id=_stable_id("v16j-rollback-decision", canonical_record_id, decision_value.value),
        canonical_record_id=canonical_record_id,
        decision=decision_value,
        marker_written=marker_written,
    )
    audit = CanonicalMemoryRollbackAuditRecord(_stable_id("v16j-rollback-audit", decision.decision_id), canonical_record_id, str(marker_file))
    return {
        "phase": "Runtime V1.6J",
        "request": request.as_dict(),
        "decision": decision.as_dict(),
        "audit": audit.as_dict(),
        "invariant_flags": dict(RUNTIME_V16J_ROLLBACK_FLAGS),
        "final_recommendation": "PROCEED_LIMITED_GENERAL_RECALL_ROUTER_DESIGN",
    }


def is_canonical_trial_record_rolled_back(canonical_record_id: str, marker_path: str | Path = DEFAULT_ROLLBACK_MARKERS) -> bool:
    path = Path(marker_path)
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                if json.loads(line).get("canonical_record_id") == canonical_record_id:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def validate_rollback_trial_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    decision = payload["decision"]
    audit = payload["audit"]
    return (
        decision["source_record_deleted"] is False
        and decision["broad_mutation"] is False
        and audit["original_record_preserved"] is True
        and audit["provider_calls_performed"] is False
        and audit["training_triggered"] is False
        and audit["recall_mutated"] is False
        and flags["canonical_trial_rollback_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"canonical_trial_rollback_enabled", "dry_run_default"})
    )


def _write_marker(path: Path, canonical_record_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_canonical_trial_record_rolled_back(canonical_record_id, path):
        return
    marker = {"rollback_marker_id": _stable_id("v16j-rollback-marker", canonical_record_id), "canonical_record_id": canonical_record_id, "original_record_deleted": False}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(marker, sort_keys=True) + "\n")


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).splitlines() if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
