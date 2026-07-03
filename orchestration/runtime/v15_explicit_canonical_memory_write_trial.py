from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


APPROVAL_HEADER = "APPROVE_CANONICAL_MEMORY_WRITE"
APPROVAL_APPROVED_BY = "approved_by=user"
APPROVAL_SCOPE = "approval_scope=single_memory_candidate_only"
DEFAULT_TRIAL_STORE = Path("data/runtime_v15i/canonical_memory_trial_records.jsonl")

RUNTIME_V15I_EXPLICIT_WRITE_TRIAL_FLAGS: dict[str, bool] = {
    "explicit_user_approved_write_trial_enabled": True,
    "single_local_trial_write_path_enabled": True,
    "general_memory_enabled": False,
    "active_canonical_memory_enabled": False,
    "runtime_recall_active": False,
    "runtime_recall_mutation_enabled": False,
    "recall_bridge_active": False,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "scheduler_enabled": False,
    "background_listener_enabled": False,
    "runtime_defaults_changed": False,
}


class ExplicitWriteTrialOutcome(str, Enum):
    WRITTEN = "written"
    BLOCKED_APPROVAL_MISSING = "blocked_approval_missing"
    BLOCKED_APPROVAL_MISMATCH = "blocked_approval_mismatch"
    BLOCKED_INVALID_CANDIDATE = "blocked_invalid_candidate"


@dataclass(frozen=True)
class ExplicitCanonicalWriteApproval:
    approval_id: str
    memory_candidate_id: str
    approval_text: str
    required_header: str = APPROVAL_HEADER
    required_approved_by: str = APPROVAL_APPROVED_BY
    required_scope: str = APPROVAL_SCOPE
    approval_present: bool = False
    approval_matches_required_structure: bool = False
    candidate_id_matches: bool = False
    bulk_approval: bool = False
    approved_by: str = "human_operator"

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryTrialRecord:
    canonical_record_id: str
    memory_candidate_id: str
    record_text: str
    provenance_reference_ids: tuple[str, ...]
    source: str = "v15i_explicit_user_approved_trial"
    lane: str = "delta_runtime_self_knowledge"
    active_for_recall: bool = False
    general_memory_enabled: bool = False
    provider_generated: bool = False
    training_example: bool = False
    created_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryTrialAuditMetadata:
    audit_id: str
    canonical_record_id: str
    memory_candidate_id: str
    approval_id: str
    audit_summary: str
    provider_calls_performed: bool = False
    tool_calls_performed: bool = False
    action_execution_performed: bool = False
    training_triggered: bool = False
    recall_mutated: bool = False
    hyb1_activated_by_default: bool = False
    model_b_default_changed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class CanonicalMemoryTrialRollbackReference:
    rollback_reference_id: str
    canonical_record_id: str
    store_path: str
    rollback_summary: str
    rollback_available_for_future_review: bool = True
    rollback_executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ExplicitCanonicalWriteTrialResult:
    result_id: str
    outcome: ExplicitWriteTrialOutcome
    memory_candidate_id: str
    canonical_record_id: str = ""
    store_path: str = ""
    record_written: bool = False
    recall_still_inactive: bool = True
    provider_calls_performed: bool = False
    tool_calls_performed: bool = False
    action_execution_performed: bool = False
    training_triggered: bool = False
    hyb1_default_activation_enabled: bool = False
    model_b_default_changed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def build_explicit_canonical_write_approval(memory_candidate: dict[str, object], approval_text: str) -> ExplicitCanonicalWriteApproval:
    candidate_id = str(memory_candidate.get("memory_candidate_id", ""))
    normalized_approval = _normalize_approval_text(approval_text)
    parsed = _parse_approval(normalized_approval)
    structure_ok = (
        parsed.get("header") == APPROVAL_HEADER
        and parsed.get("candidate_id") == candidate_id
        and parsed.get("approved_by") == "user"
        and parsed.get("approval_scope") == "single_memory_candidate_only"
        and parsed.get("line_count") == 4
    )
    return ExplicitCanonicalWriteApproval(
        approval_id=_stable_id("v15i-approval", candidate_id, normalized_approval),
        memory_candidate_id=candidate_id,
        approval_text=normalized_approval,
        approval_present=bool(normalized_approval),
        approval_matches_required_structure=structure_ok,
        candidate_id_matches=parsed.get("candidate_id") == candidate_id,
        bulk_approval=parsed.get("approval_scope") not in ("", "single_memory_candidate_only"),
    )


def execute_explicit_canonical_memory_write_trial(
    memory_candidate: dict[str, object],
    approval_text: str,
    store_path: str | Path = DEFAULT_TRIAL_STORE,
) -> dict[str, object]:
    approval = build_explicit_canonical_write_approval(memory_candidate, approval_text)
    store = Path(store_path)
    candidate_id = str(memory_candidate.get("memory_candidate_id", ""))
    candidate_text = str(memory_candidate.get("proposed_memory_text", "")).strip()
    provenance = tuple(str(item) for item in memory_candidate.get("provenance_reference_ids", ()))
    if not candidate_id or not candidate_text:
        result = _blocked_result(ExplicitWriteTrialOutcome.BLOCKED_INVALID_CANDIDATE, candidate_id)
        return _trial_payload(memory_candidate, approval, None, None, None, result)
    if not approval.approval_present:
        result = _blocked_result(ExplicitWriteTrialOutcome.BLOCKED_APPROVAL_MISSING, candidate_id)
        return _trial_payload(memory_candidate, approval, None, None, None, result)
    if not approval.approval_matches_required_structure:
        result = _blocked_result(ExplicitWriteTrialOutcome.BLOCKED_APPROVAL_MISMATCH, candidate_id)
        return _trial_payload(memory_candidate, approval, None, None, None, result)

    record_text = _canonicalize_trial_record_text(candidate_text)
    record = CanonicalMemoryTrialRecord(
        canonical_record_id=_stable_id("v15i-canonical-trial-record", candidate_id, record_text, provenance),
        memory_candidate_id=candidate_id,
        record_text=record_text,
        provenance_reference_ids=provenance,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    audit = CanonicalMemoryTrialAuditMetadata(
        audit_id=_stable_id("v15i-canonical-trial-audit", record.canonical_record_id, approval.approval_id),
        canonical_record_id=record.canonical_record_id,
        memory_candidate_id=candidate_id,
        approval_id=approval.approval_id,
        audit_summary="One explicit-approval local canonical trial record was written; recall remains inactive and no provider/tool/action/training path ran.",
    )
    rollback = CanonicalMemoryTrialRollbackReference(
        rollback_reference_id=_stable_id("v15i-canonical-trial-rollback", record.canonical_record_id, str(store)),
        canonical_record_id=record.canonical_record_id,
        store_path=str(store),
        rollback_summary="Future rollback may remove this exact trial record by canonical_record_id after explicit authorization; V1.5I does not execute rollback.",
    )
    _write_trial_record_once(store, record, audit, rollback)
    result = ExplicitCanonicalWriteTrialResult(
        result_id=_stable_id("v15i-canonical-trial-result", record.canonical_record_id, store),
        outcome=ExplicitWriteTrialOutcome.WRITTEN,
        memory_candidate_id=candidate_id,
        canonical_record_id=record.canonical_record_id,
        store_path=str(store),
        record_written=True,
    )
    return _trial_payload(memory_candidate, approval, record, audit, rollback, result)


def validate_explicit_write_trial_safe(payload: dict[str, object]) -> bool:
    result = payload["result"]
    flags = payload["invariant_flags"]
    record = payload.get("canonical_record")
    audit = payload.get("audit_metadata")
    rollback = payload.get("rollback_reference")
    record_safe = record is None or (
        record["active_for_recall"] is False
        and record["general_memory_enabled"] is False
        and record["provider_generated"] is False
        and record["training_example"] is False
    )
    audit_safe = audit is None or (
        audit["provider_calls_performed"] is False
        and audit["tool_calls_performed"] is False
        and audit["action_execution_performed"] is False
        and audit["training_triggered"] is False
        and audit["recall_mutated"] is False
        and audit["hyb1_activated_by_default"] is False
        and audit["model_b_default_changed"] is False
    )
    rollback_safe = rollback is None or rollback["rollback_executed"] is False
    return (
        record_safe
        and audit_safe
        and rollback_safe
        and result["recall_still_inactive"] is True
        and result["provider_calls_performed"] is False
        and result["tool_calls_performed"] is False
        and result["action_execution_performed"] is False
        and result["training_triggered"] is False
        and result["hyb1_default_activation_enabled"] is False
        and result["model_b_default_changed"] is False
        and flags["explicit_user_approved_write_trial_enabled"] is True
        and flags["single_local_trial_write_path_enabled"] is True
        and all(value is False for key, value in flags.items() if key not in {"explicit_user_approved_write_trial_enabled", "single_local_trial_write_path_enabled"})
    )


def _write_trial_record_once(
    store: Path,
    record: CanonicalMemoryTrialRecord,
    audit: CanonicalMemoryTrialAuditMetadata,
    rollback: CanonicalMemoryTrialRollbackReference,
) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    if store.exists():
        for line in store.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing_ids.add(json.loads(line).get("canonical_record_id", ""))
            except json.JSONDecodeError:
                continue
    if record.canonical_record_id in existing_ids:
        return
    payload = {
        **record.as_dict(),
        "audit_metadata": audit.as_dict(),
        "rollback_reference": rollback.as_dict(),
    }
    with store.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _blocked_result(outcome: ExplicitWriteTrialOutcome, candidate_id: str) -> ExplicitCanonicalWriteTrialResult:
    return ExplicitCanonicalWriteTrialResult(
        result_id=_stable_id("v15i-canonical-trial-result", outcome.value, candidate_id),
        outcome=outcome,
        memory_candidate_id=candidate_id,
    )


def _trial_payload(
    memory_candidate: dict[str, object],
    approval: ExplicitCanonicalWriteApproval,
    record: CanonicalMemoryTrialRecord | None,
    audit: CanonicalMemoryTrialAuditMetadata | None,
    rollback: CanonicalMemoryTrialRollbackReference | None,
    result: ExplicitCanonicalWriteTrialResult,
) -> dict[str, object]:
    return {
        "memory_candidate": dict(memory_candidate),
        "approval": approval.as_dict(),
        "canonical_record": record.as_dict() if record else None,
        "audit_metadata": audit.as_dict() if audit else None,
        "rollback_reference": rollback.as_dict() if rollback else None,
        "result": result.as_dict(),
        "invariant_flags": dict(RUNTIME_V15I_EXPLICIT_WRITE_TRIAL_FLAGS),
    }


def _canonicalize_trial_record_text(candidate_text: str) -> str:
    if "HYB1" in candidate_text and "dormant" in candidate_text and "Model B" in candidate_text:
        return "HYB1 remains dormant and environment-gated; Model B remains the default runtime baseline."
    return " ".join(candidate_text.split())


def _normalize_approval_text(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _parse_approval(text: str) -> dict[str, object]:
    lines = _normalize_approval_text(text).split("\n") if _normalize_approval_text(text) else []
    parsed: dict[str, object] = {"header": lines[0] if lines else "", "line_count": len(lines)}
    for line in lines[1:]:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        elif isinstance(value, Path):
            values[key] = str(value)
        elif isinstance(value, tuple):
            values[key] = [item.value if isinstance(item, Enum) else item for item in value]
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(_normalize_part(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, Path):
        return str(part)
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
