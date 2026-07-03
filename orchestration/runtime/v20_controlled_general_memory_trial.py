from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


APPROVAL_HEADER = "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE"
APPROVAL_APPROVED_BY = "approved_by=user"
APPROVAL_SCOPE = "approval_scope=single_memory_candidate_only"
DEFAULT_RECORD_STORE = Path("data/runtime_v20c/controlled_general_memory_records.jsonl")
DEFAULT_AUDIT_STORE = Path("data/runtime_v20c/controlled_general_memory_audit.jsonl")

RUNTIME_V20C_FLAGS: dict[str, bool] = {
    "controlled_general_memory_trial_enabled": True,
    "explicit_approval_required": True,
    "provider_direct_write_allowed": False,
    "evaluator_direct_write_allowed": False,
    "autonomous_write_allowed": False,
    "recall_mutated": False,
    "authoritative_recall_enabled": False,
    "training_triggered": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


class ControlledMemoryOutcome(str, Enum):
    DRY_RUN_APPROVED = "dry_run_approved"
    WRITTEN = "written"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    BLOCKED_APPROVAL_MISSING = "blocked_approval_missing"
    BLOCKED_APPROVAL_MISMATCH = "blocked_approval_mismatch"
    BLOCKED_DIRECT_PROVIDER_OR_EVALUATOR = "blocked_direct_provider_or_evaluator"


@dataclass(frozen=True)
class ControlledGeneralMemoryRecord:
    canonical_record_id: str
    candidate_id: str
    record_text: str
    provenance_reference_ids: tuple[str, ...]
    source: str = "v20c_controlled_general_memory_trial"
    active_for_recall: bool = False
    authoritative: bool = False
    created_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return {**self.__dict__, "provenance_reference_ids": list(self.provenance_reference_ids)}


def parse_controlled_memory_approval(text: str) -> dict[str, object]:
    lines = _normalize(text).split("\n") if _normalize(text) else []
    parsed: dict[str, object] = {"header": lines[0] if lines else "", "line_count": len(lines)}
    for line in lines[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    parsed["matches_required_shape"] = (
        parsed.get("header") == APPROVAL_HEADER
        and parsed.get("approved_by") == "user"
        and parsed.get("approval_scope") == "single_memory_candidate_only"
        and parsed.get("line_count") == 4
        and bool(parsed.get("candidate_id"))
    )
    return parsed


def run_controlled_general_memory_trial(
    candidate: dict[str, object],
    approval_text: str = "",
    *,
    write: bool = False,
    record_store: str | Path = DEFAULT_RECORD_STORE,
    audit_store: str | Path = DEFAULT_AUDIT_STORE,
) -> dict[str, object]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("memory_candidate_id") or "")
    source_kind = str(candidate.get("source_kind", "memory_candidate"))
    approval = parse_controlled_memory_approval(approval_text)
    if source_kind in {"provider_output", "evaluator_output", "specialist_output"}:
        return _payload(candidate_id, approval, ControlledMemoryOutcome.BLOCKED_DIRECT_PROVIDER_OR_EVALUATOR, None, False)
    if not approval_text.strip():
        return _payload(candidate_id, approval, ControlledMemoryOutcome.BLOCKED_APPROVAL_MISSING, None, False)
    if not approval.get("matches_required_shape") or approval.get("candidate_id") != candidate_id:
        return _payload(candidate_id, approval, ControlledMemoryOutcome.BLOCKED_APPROVAL_MISMATCH, None, False)

    record = _build_record(candidate_id, str(candidate.get("proposed_memory_text", candidate.get("record_text", ""))), tuple(str(item) for item in candidate.get("provenance_reference_ids", ())))
    if not write:
        return _payload(candidate_id, approval, ControlledMemoryOutcome.DRY_RUN_APPROVED, record.as_dict(), False)
    written = _append_once(Path(record_store), Path(audit_store), record, approval)
    return _payload(candidate_id, approval, ControlledMemoryOutcome.WRITTEN if written else ControlledMemoryOutcome.DUPLICATE_SKIPPED, record.as_dict(), written)


def list_controlled_general_memory_records(record_store: str | Path = DEFAULT_RECORD_STORE) -> list[dict[str, object]]:
    path = Path(record_store)
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def validate_controlled_general_memory_trial_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["result"]["recall_mutated"] is False
        and payload["result"]["training_triggered"] is False
        and payload["result"]["provider_call_performed"] is False
        and payload["result"]["autonomous_write"] is False
        and flags["controlled_general_memory_trial_enabled"] is True
        and flags["explicit_approval_required"] is True
        and all(value is False for key, value in flags.items() if key not in {"controlled_general_memory_trial_enabled", "explicit_approval_required"})
    )


def _build_record(candidate_id: str, text: str, provenance: tuple[str, ...]) -> ControlledGeneralMemoryRecord:
    normalized = " ".join(text.split())
    return ControlledGeneralMemoryRecord(
        canonical_record_id=_stable_id("v20c-record", candidate_id, normalized, provenance),
        candidate_id=candidate_id,
        record_text=normalized,
        provenance_reference_ids=provenance,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _append_once(record_store: Path, audit_store: Path, record: ControlledGeneralMemoryRecord, approval: dict[str, object]) -> bool:
    record_store.parent.mkdir(parents=True, exist_ok=True)
    audit_store.parent.mkdir(parents=True, exist_ok=True)
    existing = {item.get("canonical_record_id") for item in list_controlled_general_memory_records(record_store)}
    if record.canonical_record_id in existing:
        return False
    record_store.open("a", encoding="utf-8").write(json.dumps(record.as_dict(), sort_keys=True) + "\n")
    audit = {
        "audit_id": _stable_id("v20c-audit", record.canonical_record_id),
        "canonical_record_id": record.canonical_record_id,
        "candidate_id": record.candidate_id,
        "approval": approval,
        "rollback_reference": _stable_id("v20c-rollback", record.canonical_record_id, record_store),
        "recall_mutated": False,
        "training_triggered": False,
    }
    audit_store.open("a", encoding="utf-8").write(json.dumps(audit, sort_keys=True) + "\n")
    return True


def _payload(candidate_id: str, approval: dict[str, object], outcome: ControlledMemoryOutcome, record: dict[str, object] | None, written: bool) -> dict[str, object]:
    return {
        "phase": "Runtime V2.0C",
        "approval": approval,
        "record": record,
        "result": {
            "candidate_id": candidate_id,
            "outcome": outcome.value,
            "record_written": written,
            "recall_mutated": False,
            "training_triggered": False,
            "provider_call_performed": False,
            "autonomous_write": False,
        },
        "invariant_flags": dict(RUNTIME_V20C_FLAGS),
        "final_recommendation": "PROCEED_REVIEW_UI_WRITE_APPROVAL_BRIDGE",
    }


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
