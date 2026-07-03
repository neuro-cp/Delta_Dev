from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE


RUNTIME_V15J_RECALL_BRIDGE_FLAGS: dict[str, bool] = {
    "limited_trial_enabled": True,
    "candidate_context_only": True,
    "general_memory_enabled": False,
    "general_recall_enabled": False,
    "active_canonical_memory_enabled": False,
    "runtime_recall_mutation_enabled": False,
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


class RecallBridgeLimitedTrialOutcome(str, Enum):
    CANDIDATE_CONTEXT_AVAILABLE = "candidate_context_available"
    NO_CANDIDATE_AVAILABLE = "no_candidate_available"
    BLOCKED_UNSAFE_QUERY = "blocked_unsafe_query"
    INVALID_STORE = "invalid_store"


@dataclass(frozen=True)
class RecallBridgeCandidateContext:
    context_id: str
    canonical_record_id: str
    memory_candidate_id: str
    record_text: str
    lane: str
    provenance_reference_ids: tuple[str, ...]
    audit_reference_id: str
    rollback_reference_id: str
    candidate_context_only: bool = True
    authoritative_answer: bool = False
    truth_claim: bool = False
    active_for_recall: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class RecallBridgeLimitedTrialResult:
    result_id: str
    outcome: RecallBridgeLimitedTrialOutcome
    query: str
    context_id: str = ""
    response: str = ""
    candidate_context_returned: bool = False
    authoritative_answer: bool = False
    truth_claim: bool = False
    recall_mutated: bool = False
    provider_calls_performed: bool = False
    tool_calls_performed: bool = False
    action_execution_performed: bool = False
    training_triggered: bool = False
    hyb1_default_activation_enabled: bool = False
    model_b_default_changed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def run_limited_recall_bridge_trial(query: str, store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    normalized_query = _normalize_text(query)
    if _is_unsafe_query(normalized_query):
        result = RecallBridgeLimitedTrialResult(
            result_id=_stable_id("v15j-recall-result", normalized_query, "blocked"),
            outcome=RecallBridgeLimitedTrialOutcome.BLOCKED_UNSAFE_QUERY,
            query=query,
            response="Request blocked: V1.5J does not write, mutate, train, activate HYB1, or change defaults.",
        )
        return _trial_payload(query, None, result)

    records = _load_trial_records(Path(store_path))
    if records is None:
        result = RecallBridgeLimitedTrialResult(
            result_id=_stable_id("v15j-recall-result", normalized_query, "invalid-store"),
            outcome=RecallBridgeLimitedTrialOutcome.INVALID_STORE,
            query=query,
            response="No candidate context is available because the local trial store is invalid.",
        )
        return _trial_payload(query, None, result)

    matched = _select_single_candidate(normalized_query, records)
    if matched is None:
        result = RecallBridgeLimitedTrialResult(
            result_id=_stable_id("v15j-recall-result", normalized_query, "none"),
            outcome=RecallBridgeLimitedTrialOutcome.NO_CANDIDATE_AVAILABLE,
            query=query,
            response="No local candidate context is available for this query. General recall remains inactive.",
        )
        return _trial_payload(query, None, result)

    context = _build_context(matched)
    result = RecallBridgeLimitedTrialResult(
        result_id=_stable_id("v15j-recall-result", normalized_query, context.context_id),
        outcome=RecallBridgeLimitedTrialOutcome.CANDIDATE_CONTEXT_AVAILABLE,
        query=query,
        context_id=context.context_id,
        response=(
            "Candidate context only: "
            f"{context.record_text} "
            "This is not an authoritative answer and does not activate general recall."
        ),
        candidate_context_returned=True,
    )
    return _trial_payload(query, context, result)


def validate_limited_recall_bridge_safe(payload: dict[str, object]) -> bool:
    result = payload["result"]
    flags = payload["invariant_flags"]
    context = payload.get("candidate_context")
    context_safe = context is None or (
        context["candidate_context_only"] is True
        and context["authoritative_answer"] is False
        and context["truth_claim"] is False
        and context["active_for_recall"] is False
    )
    return (
        context_safe
        and result["authoritative_answer"] is False
        and result["truth_claim"] is False
        and result["recall_mutated"] is False
        and result["provider_calls_performed"] is False
        and result["tool_calls_performed"] is False
        and result["action_execution_performed"] is False
        and result["training_triggered"] is False
        and result["hyb1_default_activation_enabled"] is False
        and result["model_b_default_changed"] is False
        and flags["limited_trial_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"limited_trial_enabled", "candidate_context_only"})
    )


def _load_trial_records(store: Path) -> list[dict[str, object]] | None:
    if not store.exists():
        return []
    records: list[dict[str, object]] = []
    for line in store.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            return None
    return records


def _select_single_candidate(query: str, records: list[dict[str, object]]) -> dict[str, object] | None:
    if not _is_hyb1_model_b_query(query):
        return None
    candidates = [
        record
        for record in records
        if "hyb1" in _normalize_text(record.get("record_text", ""))
        and "model b" in _normalize_text(record.get("record_text", ""))
        and record.get("active_for_recall") is False
        and record.get("general_memory_enabled") is False
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _build_context(record: dict[str, object]) -> RecallBridgeCandidateContext:
    audit = record.get("audit_metadata") if isinstance(record.get("audit_metadata"), dict) else {}
    rollback = record.get("rollback_reference") if isinstance(record.get("rollback_reference"), dict) else {}
    provenance = tuple(str(item) for item in record.get("provenance_reference_ids", ()))
    canonical_record_id = str(record.get("canonical_record_id", ""))
    memory_candidate_id = str(record.get("memory_candidate_id", ""))
    return RecallBridgeCandidateContext(
        context_id=_stable_id("v15j-recall-context", canonical_record_id, memory_candidate_id),
        canonical_record_id=canonical_record_id,
        memory_candidate_id=memory_candidate_id,
        record_text=str(record.get("record_text", "")),
        lane=str(record.get("lane", "")),
        provenance_reference_ids=provenance,
        audit_reference_id=str(audit.get("audit_id", "")),
        rollback_reference_id=str(rollback.get("rollback_reference_id", "")),
    )


def _is_hyb1_model_b_query(query: str) -> bool:
    return "hyb1" in query and ("model b" in query or "default" in query or "dormant" in query)


def _is_unsafe_query(query: str) -> bool:
    unsafe_terms = (
        "write memory",
        "save memory",
        "remember this",
        "activate recall",
        "general recall",
        "promote hyb1",
        "activate hyb1",
        "train",
        "fine tune",
        "fine-tune",
        "provider",
        "tool call",
        "execute",
    )
    return any(term in query for term in unsafe_terms)


def _trial_payload(
    query: str,
    context: RecallBridgeCandidateContext | None,
    result: RecallBridgeLimitedTrialResult,
) -> dict[str, object]:
    return {
        "query": query,
        "candidate_context": context.as_dict() if context else None,
        "result": result.as_dict(),
        "invariant_flags": dict(RUNTIME_V15J_RECALL_BRIDGE_FLAGS),
    }


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


def _normalize_text(text: object) -> str:
    return " ".join(str(text).lower().split())
