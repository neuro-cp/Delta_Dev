from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from orchestration.runtime.v14_experience_adapter import (
    ExperienceBoundary,
    ExperienceBoundaryType,
    ExperienceNormalizationDecision,
    ExperienceRecord,
    ExperienceSourceMetadata,
    ExperienceSourceType,
    RawExperienceInput,
    RawExperienceInputKind,
    create_experience_boundary,
    create_experience_record,
    create_experience_source_metadata,
    create_raw_experience_input,
    decide_experience_normalization,
)
from orchestration.runtime.v14_structural_semantic_adapter import (
    SemanticAdapterDecision,
    SemanticFrame,
    SemanticFrameType,
    SemanticSignal,
    SemanticSignalPolarity,
    SemanticSignalType,
    StructuralInputKind,
    StructuralInputUnit,
    create_semantic_frame,
    create_semantic_signal,
    create_structural_input_unit,
    decide_semantic_adapter,
)


RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS: dict[str, bool] = {
    "training_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "action_execution_enabled": False,
    "tool_calls_enabled": False,
    "side_effects_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
    "live_ingestion_enabled": False,
    "background_listener_enabled": False,
    "automatic_ingestion_enabled": False,
    "active_ledger_enabled": False,
    "dry_run_execution_enabled": False,
}


@dataclass(frozen=True)
class RuntimeConsoleInput:
    console_input_id: str
    user_message: str
    source_reference: str = "manual-console-input"
    lane_scope: tuple[str, ...] = ("manual_inspection",)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "console_input_id": self.console_input_id,
            "user_message": self.user_message,
            "source_reference": self.source_reference,
            "lane_scope": list(self.lane_scope),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RuntimeConsoleSafetyStatus:
    safety_status_id: str
    disabled_capability_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS))
    review_only: bool = True
    mutation_free: bool = True
    provider_free: bool = True
    execution_free: bool = True
    no_training_data_created: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "safety_status_id": self.safety_status_id,
            "disabled_capability_flags": dict(self.disabled_capability_flags),
            "review_only": self.review_only,
            "mutation_free": self.mutation_free,
            "provider_free": self.provider_free,
            "execution_free": self.execution_free,
            "no_training_data_created": self.no_training_data_created,
        }


@dataclass(frozen=True)
class RuntimeConsoleTraceSummary:
    trace_summary_id: str
    raw_input_id: str
    experience_record_id: str
    normalization_decision_id: str
    structural_unit_id: str
    semantic_frame_id: str
    semantic_signal_id: str
    semantic_decision_id: str
    review_only: bool = True
    memory_written: bool = False
    training_triggered: bool = False
    provider_called: bool = False
    action_executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_summary_id": self.trace_summary_id,
            "raw_input_id": self.raw_input_id,
            "experience_record_id": self.experience_record_id,
            "normalization_decision_id": self.normalization_decision_id,
            "structural_unit_id": self.structural_unit_id,
            "semantic_frame_id": self.semantic_frame_id,
            "semantic_signal_id": self.semantic_signal_id,
            "semantic_decision_id": self.semantic_decision_id,
            "review_only": self.review_only,
            "memory_written": self.memory_written,
            "training_triggered": self.training_triggered,
            "provider_called": self.provider_called,
            "action_executed": self.action_executed,
        }


@dataclass(frozen=True)
class RuntimeConsolePreview:
    preview_id: str
    console_input: RuntimeConsoleInput
    source_metadata: ExperienceSourceMetadata
    raw_input: RawExperienceInput
    boundary: ExperienceBoundary
    experience_record: ExperienceRecord
    normalization_decision: ExperienceNormalizationDecision
    structural_unit: StructuralInputUnit
    semantic_frame: SemanticFrame
    semantic_signal: SemanticSignal
    semantic_decision: SemanticAdapterDecision
    safety_status: RuntimeConsoleSafetyStatus
    trace_summary: RuntimeConsoleTraceSummary
    placeholder_response: str = "Runtime console preview only. No provider, memory, training, recall, or execution path was used."

    def as_dict(self) -> dict[str, object]:
        return {
            "preview_id": self.preview_id,
            "console_input": self.console_input.as_dict(),
            "input_summary": {
                "message_length": len(self.console_input.user_message),
                "source_reference": self.console_input.source_reference,
                "lane_scope": list(self.console_input.lane_scope),
            },
            "experience_record_summary": {
                "record_id": self.experience_record.record_id,
                "eligible_for_semantic_adapter": self.experience_record.eligible_for_semantic_adapter,
                "memory": self.experience_record.memory,
                "canonical": self.experience_record.canonical,
                "learned": self.experience_record.learned,
                "active": self.experience_record.active,
            },
            "semantic_frame_summary": {
                "frame_id": self.semantic_frame.frame_id,
                "frame_type": self.semantic_frame.frame_type.value,
                "normalized_summary": self.semantic_frame.normalized_summary,
                "canonical": self.semantic_frame.canonical,
                "learned": self.semantic_frame.learned,
                "active": self.semantic_frame.active,
            },
            "trace_summary": self.trace_summary.as_dict(),
            "safety_status": self.safety_status.as_dict(),
            "placeholder_response": self.placeholder_response,
        }


@dataclass(frozen=True)
class RuntimeConsolePlan:
    plan_id: str
    preview_ids: tuple[str, ...]
    manual_only: bool = True
    review_only: bool = True
    provider_calls_enabled: bool = False
    memory_mutation_enabled: bool = False
    training_enabled: bool = False
    action_execution_enabled: bool = False
    scheduler_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "preview_ids": list(self.preview_ids),
            "manual_only": self.manual_only,
            "review_only": self.review_only,
            "provider_calls_enabled": self.provider_calls_enabled,
            "memory_mutation_enabled": self.memory_mutation_enabled,
            "training_enabled": self.training_enabled,
            "action_execution_enabled": self.action_execution_enabled,
            "scheduler_enabled": self.scheduler_enabled,
        }


def create_runtime_console_input(
    user_message: str,
    *,
    source_reference: str = "manual-console-input",
    lane_scope: tuple[str, ...] = ("manual_inspection",),
) -> RuntimeConsoleInput:
    normalized = " ".join(str(user_message).split())
    console_input_id = _stable_id("runtime-console-input", normalized, source_reference, lane_scope)
    return RuntimeConsoleInput(
        console_input_id=console_input_id,
        user_message=normalized,
        source_reference=source_reference,
        lane_scope=tuple(lane_scope),
    )


def build_runtime_console_preview(user_message: str, *, source_reference: str = "manual-console-input") -> RuntimeConsolePreview:
    console_input = create_runtime_console_input(user_message, source_reference=source_reference)
    metadata = create_experience_source_metadata(
        source_type=ExperienceSourceType.USER_DIRECT,
        source_reference=console_input.source_reference,
        provenance_notes="manual runtime console preview; not hidden capture",
    )
    raw_input = create_raw_experience_input(
        input_kind=RawExperienceInputKind.USER_MESSAGE,
        content=console_input.user_message,
        source_metadata=metadata,
        lane_scope=console_input.lane_scope,
        provenance_reference_ids=(console_input.console_input_id,),
    )
    boundary = create_experience_boundary(
        raw_input,
        boundary_type=ExperienceBoundaryType.SINGLE_MESSAGE,
        reason="manual message preview only; no auto-ingestion",
    )
    record = create_experience_record(raw_input, boundary, eligible_for_semantic_adapter=True)
    normalization_decision = decide_experience_normalization(raw_input, record)
    unit = create_structural_input_unit(
        source_reference_id=record.record_id,
        input_kind=StructuralInputKind.USER_MESSAGE,
        raw_text=record.normalized_content,
        structured_fields={"console_input_id": console_input.console_input_id},
        source_metadata=metadata.as_dict(),
        lane_scope=record.lane_scope,
        provenance_reference_ids=record.provenance_reference_ids,
        notes="manual console structural preview; not memory",
    )
    frame = create_semantic_frame(
        unit=unit,
        frame_type=_frame_type_for_message(record.normalized_content),
        normalized_summary=_summarize_message(record.normalized_content),
        uncertainty_notes=("manual preview only",),
        notes="semantic frame preview only; not learned",
    )
    signal = create_semantic_signal(
        frame=frame,
        signal_type=_signal_type_for_message(record.normalized_content),
        polarity=SemanticSignalPolarity.REQUIRES_REVIEW,
        severity_or_weight=0.1,
        rationale="manual console input may be inspected but not learned",
        source_reference_ids=(raw_input.input_id,),
        provenance_reference_ids=record.provenance_reference_ids,
    )
    semantic_decision = decide_semantic_adapter(unit, frames=(frame,), signals=(signal,))
    safety_status = create_runtime_console_safety_status(console_input.console_input_id)
    trace_summary = create_runtime_console_trace_summary(
        raw_input=raw_input,
        record=record,
        normalization_decision=normalization_decision,
        structural_unit=unit,
        semantic_frame=frame,
        semantic_signal=signal,
        semantic_decision=semantic_decision,
    )
    preview_id = _stable_id("runtime-console-preview", console_input.console_input_id, trace_summary.trace_summary_id)
    return RuntimeConsolePreview(
        preview_id=preview_id,
        console_input=console_input,
        source_metadata=metadata,
        raw_input=raw_input,
        boundary=boundary,
        experience_record=record,
        normalization_decision=normalization_decision,
        structural_unit=unit,
        semantic_frame=frame,
        semantic_signal=signal,
        semantic_decision=semantic_decision,
        safety_status=safety_status,
        trace_summary=trace_summary,
    )


def create_runtime_console_safety_status(source_id: str = "runtime-console") -> RuntimeConsoleSafetyStatus:
    safety_status_id = _stable_id("runtime-console-safety", source_id, RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS)
    return RuntimeConsoleSafetyStatus(safety_status_id=safety_status_id)


def create_runtime_console_trace_summary(
    *,
    raw_input: RawExperienceInput,
    record: ExperienceRecord,
    normalization_decision: ExperienceNormalizationDecision,
    structural_unit: StructuralInputUnit,
    semantic_frame: SemanticFrame,
    semantic_signal: SemanticSignal,
    semantic_decision: SemanticAdapterDecision,
) -> RuntimeConsoleTraceSummary:
    trace_summary_id = _stable_id(
        "runtime-console-trace",
        raw_input.input_id,
        record.record_id,
        normalization_decision.decision_id,
        structural_unit.unit_id,
        semantic_frame.frame_id,
        semantic_signal.signal_id,
        semantic_decision.decision_id,
    )
    return RuntimeConsoleTraceSummary(
        trace_summary_id=trace_summary_id,
        raw_input_id=raw_input.input_id,
        experience_record_id=record.record_id,
        normalization_decision_id=normalization_decision.decision_id,
        structural_unit_id=structural_unit.unit_id,
        semantic_frame_id=semantic_frame.frame_id,
        semantic_signal_id=semantic_signal.signal_id,
        semantic_decision_id=semantic_decision.decision_id,
    )


def create_runtime_console_plan(previews: tuple[RuntimeConsolePreview, ...]) -> RuntimeConsolePlan:
    preview_ids = tuple(sorted(preview.preview_id for preview in previews))
    plan_id = _stable_id("runtime-console-plan", preview_ids)
    return RuntimeConsolePlan(plan_id=plan_id, preview_ids=preview_ids)


def validate_runtime_console_preview_review_only(preview: RuntimeConsolePreview) -> bool:
    flags = preview.safety_status.disabled_capability_flags
    return (
        preview.safety_status.review_only
        and preview.safety_status.mutation_free
        and preview.safety_status.provider_free
        and preview.safety_status.execution_free
        and preview.safety_status.no_training_data_created
        and all(value is False for value in flags.values())
        and preview.raw_input.memory is False
        and preview.raw_input.training_example is False
        and preview.raw_input.ingested_automatically is False
        and preview.experience_record.memory is False
        and preview.experience_record.canonical is False
        and preview.experience_record.learned is False
        and preview.semantic_frame.canonical is False
        and preview.semantic_frame.learned is False
        and preview.trace_summary.memory_written is False
        and preview.trace_summary.training_triggered is False
        and preview.trace_summary.provider_called is False
        and preview.trace_summary.action_executed is False
    )


def validate_runtime_console_plan_inert(plan: RuntimeConsolePlan) -> bool:
    return plan.manual_only and plan.review_only and not any(
        (
            plan.provider_calls_enabled,
            plan.memory_mutation_enabled,
            plan.training_enabled,
            plan.action_execution_enabled,
            plan.scheduler_enabled,
        )
    )


def _frame_type_for_message(message: str) -> SemanticFrameType:
    lowered = message.lower()
    if "?" in message:
        return SemanticFrameType.QUESTION
    if any(term in lowered for term in ("please", "do ", "create", "update", "delete", "send", "call")):
        return SemanticFrameType.ACTION_INTENT_CANDIDATE
    return SemanticFrameType.OBSERVATION


def _signal_type_for_message(message: str) -> SemanticSignalType:
    lowered = message.lower()
    if any(term in lowered for term in ("create", "update", "delete", "send", "call", "write")):
        return SemanticSignalType.POSSIBLE_ACTION_INTENT
    if "?" in message:
        return SemanticSignalType.POSSIBLE_UNKNOWN
    return SemanticSignalType.REQUIRES_HUMAN_REVIEW


def _summarize_message(message: str, *, max_length: int = 120) -> str:
    normalized = " ".join(str(message).split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _stable_id(prefix: str, *parts: object) -> str:
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
