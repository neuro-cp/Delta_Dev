from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14M_INVARIANT_FLAGS: dict[str, bool] = {
    "experience_adapter_enabled": False,
    "live_ingestion_enabled": False,
    "automatic_ingestion_enabled": False,
    "background_listener_enabled": False,
    "semantic_adapter_integration_enabled": False,
    "candidate_envelope_write_enabled": False,
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "scheduler_enabled": False,
    "execution_enabled": False,
    "runtime_defaults_changed": False,
}


class RawExperienceInputKind(str, Enum):
    USER_MESSAGE = "user_message"
    OBSERVATION = "observation"
    FEEDBACK = "feedback"
    CORRECTION = "correction"
    TOOL_OUTPUT_PLACEHOLDER = "tool_output_placeholder"
    UI_EVENT_PLACEHOLDER = "ui_event_placeholder"
    SYSTEM_NOTE = "system_note"
    UNKNOWN = "unknown"


class ExperienceSourceType(str, Enum):
    USER_DIRECT = "user_direct"
    SYSTEM_INTERNAL = "system_internal"
    TOOL_PLACEHOLDER = "tool_placeholder"
    UI_EVENT_PLACEHOLDER = "ui_event_placeholder"
    TEST_FIXTURE = "test_fixture"
    UNKNOWN = "unknown"


class ExperienceBoundaryType(str, Enum):
    SINGLE_MESSAGE = "single_message"
    EXPLICIT_FEEDBACK = "explicit_feedback"
    EXPLICIT_OBSERVATION = "explicit_observation"
    EXPLICIT_CORRECTION = "explicit_correction"
    TOOL_OUTPUT_PLACEHOLDER = "tool_output_placeholder"
    UI_EVENT_PLACEHOLDER = "ui_event_placeholder"
    TEST_FIXTURE = "test_fixture"


class ExperienceNormalizationOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    RECORD_ONLY = "record_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_STRUCTURAL_SEMANTIC_ADAPTER = "eligible_for_structural_semantic_adapter"


@dataclass(frozen=True)
class ExperienceSourceMetadata:
    metadata_id: str
    source_type: ExperienceSourceType
    source_reference: str
    user_visible: bool = True
    trusted_source: bool = False
    provenance_notes: str = ""
    hidden_capture: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "metadata_id": self.metadata_id,
            "source_type": self.source_type.value,
            "source_reference": self.source_reference,
            "user_visible": self.user_visible,
            "trusted_source": self.trusted_source,
            "provenance_notes": self.provenance_notes,
            "hidden_capture": self.hidden_capture,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RawExperienceInput:
    input_id: str
    input_kind: RawExperienceInputKind
    content: str
    source_metadata: ExperienceSourceMetadata
    received_at: str = "static-test-received-at"
    lane_scope: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    active: bool = False
    memory: bool = False
    training_example: bool = False
    ingested_automatically: bool = False
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "input_id": self.input_id,
            "input_kind": self.input_kind.value,
            "content": self.content,
            "source_metadata": self.source_metadata.as_dict(),
            "received_at": self.received_at,
            "lane_scope": list(self.lane_scope),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "active": self.active,
            "memory": self.memory,
            "training_example": self.training_example,
            "ingested_automatically": self.ingested_automatically,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ExperienceBoundary:
    boundary_id: str
    input_id: str
    boundary_type: ExperienceBoundaryType
    included_content_reference: str
    excluded_content_notes: tuple[str, ...] = ()
    reason: str = ""
    automatic_ingestion_enabled: bool = False
    background_listener_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "boundary_id": self.boundary_id,
            "input_id": self.input_id,
            "boundary_type": self.boundary_type.value,
            "included_content_reference": self.included_content_reference,
            "excluded_content_notes": list(self.excluded_content_notes),
            "reason": self.reason,
            "automatic_ingestion_enabled": self.automatic_ingestion_enabled,
            "background_listener_enabled": self.background_listener_enabled,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExperienceRecord:
    record_id: str
    input_id: str
    boundary_id: str
    normalized_content: str
    source_metadata_id: str
    lane_scope: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    eligible_for_semantic_adapter: bool = False
    memory: bool = False
    canonical: bool = False
    learned: bool = False
    active: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "input_id": self.input_id,
            "boundary_id": self.boundary_id,
            "normalized_content": self.normalized_content,
            "source_metadata_id": self.source_metadata_id,
            "lane_scope": list(self.lane_scope),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "eligible_for_semantic_adapter": self.eligible_for_semantic_adapter,
            "memory": self.memory,
            "canonical": self.canonical,
            "learned": self.learned,
            "active": self.active,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ExperienceNormalizationDecision:
    decision_id: str
    input_id: str
    record_id: str = ""
    outcome: ExperienceNormalizationOutcome = ExperienceNormalizationOutcome.DEFER
    rationale: str = ""
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14M_INVARIANT_FLAGS))
    applied: bool = False
    memory_written: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "input_id": self.input_id,
            "record_id": self.record_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "memory_written": self.memory_written,
            "training_triggered": self.training_triggered,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExperienceAdapterTrace:
    trace_id: str
    input_id: str
    boundary_id: str
    record_id: str
    decision_id: str
    source_reference_ids: tuple[str, ...] = ()
    generated_for_review_only: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class ExperienceAdapterPlan:
    plan_id: str
    input_ids: tuple[str, ...] = ()
    record_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    experience_adapter_enabled: bool = False
    live_ingestion_enabled: bool = False
    automatic_ingestion_enabled: bool = False
    background_listener_enabled: bool = False
    semantic_adapter_integration_enabled: bool = False
    candidate_envelope_write_enabled: bool = False
    canonical_write_enabled: bool = False
    active_store_enabled: bool = False
    memory_mutation_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    training_enabled: bool = False
    provider_calls_enabled: bool = False
    specialist_routing_enabled: bool = False
    scheduler_enabled: bool = False
    execution_enabled: bool = False
    runtime_defaults_changed: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14M_INVARIANT_FLAGS))


@dataclass(frozen=True)
class ExperienceAdapterReportEntry:
    report_entry_id: str
    trace_id: str
    input_summary: str
    boundary_summary: str
    record_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = ""
    generated_for_review_only: bool = True


def create_experience_source_metadata(
    *, source_type: ExperienceSourceType, source_reference: str, user_visible: bool = True, trusted_source: bool = False, provenance_notes: str = ""
) -> ExperienceSourceMetadata:
    return ExperienceSourceMetadata(
        metadata_id=_stable_id("experience-source", source_type.value, source_reference, user_visible, trusted_source, provenance_notes),
        source_type=source_type,
        source_reference=source_reference,
        user_visible=user_visible,
        trusted_source=trusted_source,
        provenance_notes=provenance_notes,
    )


def create_raw_experience_input(
    *, input_kind: RawExperienceInputKind, content: str, source_metadata: ExperienceSourceMetadata, lane_scope: tuple[str, ...] = (), provenance_reference_ids: tuple[str, ...] = ()
) -> RawExperienceInput:
    return RawExperienceInput(
        input_id=_stable_id("raw-experience", input_kind.value, content, source_metadata.metadata_id, lane_scope, provenance_reference_ids),
        input_kind=input_kind,
        content=content,
        source_metadata=source_metadata,
        lane_scope=lane_scope,
        provenance_reference_ids=provenance_reference_ids,
        notes="raw input is bounded input, not memory",
    )


def create_experience_boundary(
    raw_input: RawExperienceInput, *, boundary_type: ExperienceBoundaryType, excluded_content_notes: tuple[str, ...] = (), reason: str = ""
) -> ExperienceBoundary:
    return ExperienceBoundary(
        boundary_id=_stable_id("experience-boundary", raw_input.input_id, boundary_type.value, excluded_content_notes, reason),
        input_id=raw_input.input_id,
        boundary_type=boundary_type,
        included_content_reference=raw_input.input_id,
        excluded_content_notes=excluded_content_notes,
        reason=reason or "explicit bounded input only",
    )


def create_experience_record(raw_input: RawExperienceInput, boundary: ExperienceBoundary, *, eligible_for_semantic_adapter: bool = False) -> ExperienceRecord:
    normalized = " ".join(raw_input.content.split())
    return ExperienceRecord(
        record_id=_stable_id("experience-record", raw_input.input_id, boundary.boundary_id, normalized),
        input_id=raw_input.input_id,
        boundary_id=boundary.boundary_id,
        normalized_content=normalized,
        source_metadata_id=raw_input.source_metadata.metadata_id,
        lane_scope=raw_input.lane_scope,
        provenance_reference_ids=raw_input.provenance_reference_ids,
        eligible_for_semantic_adapter=eligible_for_semantic_adapter,
        notes="experience record is bounded observation only, not learned state",
    )


def decide_experience_normalization(raw_input: RawExperienceInput, record: ExperienceRecord | None = None, *, require_human_review: bool = False, force_blocked: bool = False) -> ExperienceNormalizationDecision:
    if force_blocked or any(value is True for value in RUNTIME_V14M_INVARIANT_FLAGS.values()):
        outcome = ExperienceNormalizationOutcome.BLOCKED_BY_INVARIANT
        rationale = "Experience adapter blocked by invariant."
    elif require_human_review:
        outcome = ExperienceNormalizationOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Experience input requires human review."
    elif record and record.eligible_for_semantic_adapter:
        outcome = ExperienceNormalizationOutcome.ELIGIBLE_FOR_STRUCTURAL_SEMANTIC_ADAPTER
        rationale = "Record may be reviewed by structural semantic adapter later."
    elif record:
        outcome = ExperienceNormalizationOutcome.RECORD_ONLY
        rationale = "Record may remain as bounded observation only."
    else:
        outcome = ExperienceNormalizationOutcome.DEFER
        rationale = "Input lacks a normalized record."
    return ExperienceNormalizationDecision(
        decision_id=_stable_id("experience-decision", raw_input.input_id, record.record_id if record else "", outcome.value),
        input_id=raw_input.input_id,
        record_id=record.record_id if record else "",
        outcome=outcome,
        rationale=rationale,
    )


def create_experience_adapter_trace(raw_input: RawExperienceInput, boundary: ExperienceBoundary, record: ExperienceRecord, decision: ExperienceNormalizationDecision) -> ExperienceAdapterTrace:
    return ExperienceAdapterTrace(
        trace_id=_stable_id("experience-trace", raw_input.input_id, boundary.boundary_id, record.record_id, decision.decision_id),
        input_id=raw_input.input_id,
        boundary_id=boundary.boundary_id,
        record_id=record.record_id,
        decision_id=decision.decision_id,
        source_reference_ids=(raw_input.source_metadata.source_reference,),
    )


def create_experience_adapter_plan(inputs: tuple[RawExperienceInput, ...] = (), records: tuple[ExperienceRecord, ...] = (), decisions: tuple[ExperienceNormalizationDecision, ...] = ()) -> ExperienceAdapterPlan:
    input_ids = tuple(sorted(item.input_id for item in inputs))
    record_ids = tuple(sorted(item.record_id for item in records))
    decision_ids = tuple(sorted(item.decision_id for item in decisions))
    return ExperienceAdapterPlan(plan_id=_stable_id("experience-plan", input_ids, record_ids, decision_ids), input_ids=input_ids, record_ids=record_ids, decision_ids=decision_ids)


def create_experience_adapter_report_entry(trace: ExperienceAdapterTrace, raw_input: RawExperienceInput, boundary: ExperienceBoundary, record: ExperienceRecord, decision: ExperienceNormalizationDecision) -> ExperienceAdapterReportEntry:
    return ExperienceAdapterReportEntry(
        report_entry_id=_stable_id("experience-report-entry", trace.trace_id, decision.outcome.value),
        trace_id=trace.trace_id,
        input_summary=f"{raw_input.input_kind.value}: not memory",
        boundary_summary=f"{boundary.boundary_type.value}: no ingestion daemon",
        record_summary="experience record is inactive and non-canonical",
        decision_summary=decision.outcome.value,
        unresolved_gaps=("semantic adapter integration disabled",),
        recommended_next_review_step="active specialist routing design gated",
    )


def validate_source_metadata_non_hidden(metadata: ExperienceSourceMetadata) -> bool:
    return metadata.hidden_capture is False


def validate_raw_experience_input_inert(raw_input: RawExperienceInput) -> bool:
    return raw_input.active is False and raw_input.memory is False and raw_input.training_example is False and raw_input.ingested_automatically is False


def validate_experience_boundary_inert(boundary: ExperienceBoundary) -> bool:
    return boundary.automatic_ingestion_enabled is False and boundary.background_listener_enabled is False


def validate_experience_record_inert(record: ExperienceRecord) -> bool:
    return record.memory is False and record.canonical is False and record.learned is False and record.active is False


def validate_experience_decision_review_only(decision: ExperienceNormalizationDecision) -> bool:
    return decision.applied is False and decision.memory_written is False and decision.training_triggered is False and all(value is False for value in decision.invariant_flags.values())


def validate_experience_trace_review_only(trace: ExperienceAdapterTrace) -> bool:
    return trace.generated_for_review_only is True and trace.applied is False


def validate_experience_plan_inert(plan: ExperienceAdapterPlan) -> bool:
    return (
        plan.experience_adapter_enabled is False
        and plan.live_ingestion_enabled is False
        and plan.automatic_ingestion_enabled is False
        and plan.background_listener_enabled is False
        and plan.semantic_adapter_integration_enabled is False
        and plan.candidate_envelope_write_enabled is False
        and plan.canonical_write_enabled is False
        and plan.memory_mutation_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.training_enabled is False
        and plan.provider_calls_enabled is False
        and plan.specialist_routing_enabled is False
        and plan.scheduler_enabled is False
        and plan.execution_enabled is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_experience_report_entry_review_only(entry: ExperienceAdapterReportEntry) -> bool:
    return entry.generated_for_review_only is True


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(_normalize_part(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _normalize_part(part: object) -> str:
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
