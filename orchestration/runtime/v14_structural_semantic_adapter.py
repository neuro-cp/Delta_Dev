from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14L_INVARIANT_FLAGS: dict[str, bool] = {
    "semantic_adapter_enabled": False,
    "live_adaptation_enabled": False,
    "candidate_envelope_write_enabled": False,
    "canonical_write_enabled": False,
    "active_store_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "pruning_enabled": False,
    "canonical_pruning_enabled": False,
    "projection_application_enabled": False,
    "provider_calls_enabled": False,
    "specialist_routing_enabled": False,
    "scheduler_enabled": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
    "activation_integration_enabled": False,
    "attention_integration_enabled": False,
    "evidence_selection_integration_enabled": False,
    "runtime_defaults_changed": False,
}


class StructuralInputKind(str, Enum):
    USER_MESSAGE = "user_message"
    OBSERVATION = "observation"
    FEEDBACK = "feedback"
    CORRECTION = "correction"
    QUESTION = "question"
    ANSWER_TRACE = "answer_trace"
    EVIDENCE_TRACE = "evidence_trace"
    SPECIALIST_CLAIM = "specialist_claim"
    HYPOTHESIS_CLAIM = "hypothesis_claim"
    RECALL_QUERY = "recall_query"
    TOOL_OUTPUT_PLACEHOLDER = "tool_output_placeholder"
    UNKNOWN = "unknown"


class SemanticFrameType(str, Enum):
    CLAIM = "claim"
    QUESTION = "question"
    CORRECTION = "correction"
    INSTRUCTION = "instruction"
    OBSERVATION = "observation"
    FEEDBACK = "feedback"
    EVIDENCE = "evidence"
    CONTRADICTION = "contradiction"
    UNCERTAINTY = "uncertainty"
    ACTION_INTENT_CANDIDATE = "action_intent_candidate"
    MEMORY_CANDIDATE_SHAPE = "memory_candidate_shape"
    UNKNOWN = "unknown"


class SemanticRoleType(str, Enum):
    USER_CLAIM = "user_claim"
    SYSTEM_CLAIM = "system_claim"
    EVIDENCE_SOURCE = "evidence_source"
    CORRECTION_SIGNAL = "correction_signal"
    CONTRADICTION_SIGNAL = "contradiction_signal"
    UNCERTAINTY_SIGNAL = "uncertainty_signal"
    INSTRUCTION_CANDIDATE = "instruction_candidate"
    ACTION_CANDIDATE = "action_candidate"
    MEMORY_CANDIDATE = "memory_candidate"
    SAFETY_RELEVANT = "safety_relevant"
    UNKNOWN = "unknown"


class SemanticSignalType(str, Enum):
    POSSIBLE_MEMORY_CANDIDATE = "possible_memory_candidate"
    POSSIBLE_FEEDBACK = "possible_feedback"
    POSSIBLE_CORRECTION = "possible_correction"
    POSSIBLE_CONTRADICTION = "possible_contradiction"
    POSSIBLE_ACTION_INTENT = "possible_action_intent"
    POSSIBLE_UNKNOWN = "possible_unknown"
    INSUFFICIENT_STRUCTURE = "insufficient_structure"
    PROVENANCE_GAP = "provenance_gap"
    LANE_SCOPE_AMBIGUOUS = "lane_scope_ambiguous"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


class SemanticSignalPolarity(str, Enum):
    SUPPORTS_ADAPTATION = "supports_adaptation"
    BLOCKS_ADAPTATION = "blocks_adaptation"
    REQUIRES_REVIEW = "requires_review"
    NEUTRAL = "neutral"


class SemanticAdapterOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    FRAME_ONLY = "frame_only"
    SIGNAL_ONLY = "signal_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_CANDIDATE_ENVELOPE = "eligible_for_future_candidate_envelope"
    ELIGIBLE_FOR_FUTURE_EXPERIENCE_RECORD = "eligible_for_future_experience_record"


@dataclass(frozen=True)
class StructuralInputUnit:
    unit_id: str
    source_reference_id: str
    input_kind: StructuralInputKind
    raw_text: str = ""
    structured_fields: dict[str, object] = field(default_factory=dict)
    source_metadata: dict[str, object] = field(default_factory=dict)
    lane_scope: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    active: bool = False
    memory: bool = False
    training_example: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "unit_id": self.unit_id,
            "source_reference_id": self.source_reference_id,
            "input_kind": self.input_kind.value,
            "raw_text": self.raw_text,
            "structured_fields": dict(self.structured_fields),
            "source_metadata": dict(self.source_metadata),
            "lane_scope": list(self.lane_scope),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "active": self.active,
            "memory": self.memory,
            "training_example": self.training_example,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticFrame:
    frame_id: str
    unit_id: str
    frame_type: SemanticFrameType
    normalized_summary: str
    entity_references: tuple[str, ...] = ()
    claim_references: tuple[str, ...] = ()
    action_references: tuple[str, ...] = ()
    uncertainty_notes: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    canonical: bool = False
    learned: bool = False
    active: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "unit_id": self.unit_id,
            "frame_type": self.frame_type.value,
            "normalized_summary": self.normalized_summary,
            "entity_references": list(self.entity_references),
            "claim_references": list(self.claim_references),
            "action_references": list(self.action_references),
            "uncertainty_notes": list(self.uncertainty_notes),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "lane_scope": list(self.lane_scope),
            "canonical": self.canonical,
            "learned": self.learned,
            "active": self.active,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticRoleAssignment:
    assignment_id: str
    frame_id: str
    target_reference: str
    role_type: SemanticRoleType
    lane_scope: tuple[str, ...] = ()
    rationale: str = ""
    confidence_state: float = 0.0
    authoritative: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return _clamp(self.confidence_state)

    def as_dict(self) -> dict[str, object]:
        return {
            "assignment_id": self.assignment_id,
            "frame_id": self.frame_id,
            "target_reference": self.target_reference,
            "role_type": self.role_type.value,
            "lane_scope": list(self.lane_scope),
            "rationale": self.rationale,
            "confidence_state": self.normalized_confidence(),
            "authoritative": self.authoritative,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticSignal:
    signal_id: str
    frame_id: str
    signal_type: SemanticSignalType
    polarity: SemanticSignalPolarity
    severity_or_weight: float = 0.0
    rationale: str = ""
    source_reference_ids: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    active: bool = False
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_weight(self) -> float:
        return _clamp(self.severity_or_weight)

    def as_dict(self) -> dict[str, object]:
        return {
            "signal_id": self.signal_id,
            "frame_id": self.frame_id,
            "signal_type": self.signal_type.value,
            "polarity": self.polarity.value,
            "severity_or_weight": self.normalized_weight(),
            "rationale": self.rationale,
            "source_reference_ids": list(self.source_reference_ids),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "active": self.active,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticAdapterDecision:
    decision_id: str
    unit_id: str
    frame_ids: tuple[str, ...] = ()
    signal_ids: tuple[str, ...] = ()
    outcome: SemanticAdapterOutcome = SemanticAdapterOutcome.DEFER
    rationale: str = ""
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14L_INVARIANT_FLAGS))
    applied: bool = False
    memory_written: bool = False
    training_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "unit_id": self.unit_id,
            "frame_ids": list(self.frame_ids),
            "signal_ids": list(self.signal_ids),
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "memory_written": self.memory_written,
            "training_triggered": self.training_triggered,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticAdapterTrace:
    trace_id: str
    unit_id: str
    frame_ids: tuple[str, ...] = ()
    role_assignment_ids: tuple[str, ...] = ()
    signal_ids: tuple[str, ...] = ()
    decision_id: str = ""
    source_reference_ids: tuple[str, ...] = ()
    generated_for_review_only: bool = True
    applied: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "unit_id": self.unit_id,
            "frame_ids": list(self.frame_ids),
            "role_assignment_ids": list(self.role_assignment_ids),
            "signal_ids": list(self.signal_ids),
            "decision_id": self.decision_id,
            "source_reference_ids": list(self.source_reference_ids),
            "generated_for_review_only": self.generated_for_review_only,
            "applied": self.applied,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticAdapterPlan:
    plan_id: str
    unit_ids: tuple[str, ...] = ()
    frame_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    semantic_adapter_enabled: bool = False
    live_adaptation_enabled: bool = False
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
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14L_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "unit_ids": list(self.unit_ids),
            "frame_ids": list(self.frame_ids),
            "decision_ids": list(self.decision_ids),
            "semantic_adapter_enabled": self.semantic_adapter_enabled,
            "live_adaptation_enabled": self.live_adaptation_enabled,
            "candidate_envelope_write_enabled": self.candidate_envelope_write_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "active_store_enabled": self.active_store_enabled,
            "memory_mutation_enabled": self.memory_mutation_enabled,
            "runtime_recall_mutation_enabled": self.runtime_recall_mutation_enabled,
            "training_enabled": self.training_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "specialist_routing_enabled": self.specialist_routing_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "execution_enabled": self.execution_enabled,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticAdapterReportEntry:
    report_entry_id: str
    trace_id: str
    unit_id: str
    frame_summary: str
    role_summary: str
    signal_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = ""
    generated_for_review_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "report_entry_id": self.report_entry_id,
            "trace_id": self.trace_id,
            "unit_id": self.unit_id,
            "frame_summary": self.frame_summary,
            "role_summary": self.role_summary,
            "signal_summary": self.signal_summary,
            "decision_summary": self.decision_summary,
            "unresolved_gaps": list(self.unresolved_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_structural_input_unit(
    *,
    source_reference_id: str,
    input_kind: StructuralInputKind,
    raw_text: str = "",
    structured_fields: dict[str, object] | None = None,
    source_metadata: dict[str, object] | None = None,
    lane_scope: tuple[str, ...] | list[str] = (),
    provenance_reference_ids: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> StructuralInputUnit:
    unit_id = _stable_id("structural-input", source_reference_id, input_kind.value, raw_text, structured_fields or {}, lane_scope)
    return StructuralInputUnit(
        unit_id=unit_id,
        source_reference_id=source_reference_id,
        input_kind=input_kind,
        raw_text=raw_text,
        structured_fields=dict(structured_fields or {}),
        source_metadata=dict(source_metadata or {}),
        lane_scope=tuple(lane_scope),
        provenance_reference_ids=tuple(provenance_reference_ids),
        notes=notes or "input unit is bounded structure, not memory",
    )


def create_semantic_frame(
    *,
    unit: StructuralInputUnit,
    frame_type: SemanticFrameType,
    normalized_summary: str,
    entity_references: tuple[str, ...] | list[str] = (),
    claim_references: tuple[str, ...] | list[str] = (),
    action_references: tuple[str, ...] | list[str] = (),
    uncertainty_notes: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> SemanticFrame:
    frame_id = _stable_id("semantic-frame", unit.unit_id, frame_type.value, normalized_summary, entity_references, claim_references, action_references)
    return SemanticFrame(
        frame_id=frame_id,
        unit_id=unit.unit_id,
        frame_type=frame_type,
        normalized_summary=normalized_summary,
        entity_references=tuple(entity_references),
        claim_references=tuple(claim_references),
        action_references=tuple(action_references),
        uncertainty_notes=tuple(uncertainty_notes),
        provenance_reference_ids=unit.provenance_reference_ids,
        lane_scope=unit.lane_scope,
        notes=notes or "semantic frame is an interpretation shape, not memory",
    )


def create_semantic_role_assignment(
    *,
    frame: SemanticFrame,
    target_reference: str,
    role_type: SemanticRoleType,
    lane_scope: tuple[str, ...] | list[str] = (),
    rationale: str = "",
    confidence_state: float = 0.0,
    notes: str = "",
) -> SemanticRoleAssignment:
    assignment_id = _stable_id("semantic-role", frame.frame_id, target_reference, role_type.value, lane_scope, rationale)
    return SemanticRoleAssignment(
        assignment_id=assignment_id,
        frame_id=frame.frame_id,
        target_reference=target_reference,
        role_type=role_type,
        lane_scope=tuple(lane_scope or frame.lane_scope),
        rationale=rationale,
        confidence_state=confidence_state,
        notes=notes or "role assignment is non-authoritative and not applied",
    )


def create_semantic_signal(
    *,
    frame: SemanticFrame,
    signal_type: SemanticSignalType,
    polarity: SemanticSignalPolarity,
    severity_or_weight: float = 0.0,
    rationale: str = "",
    source_reference_ids: tuple[str, ...] | list[str] = (),
    provenance_reference_ids: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> SemanticSignal:
    signal_id = _stable_id("semantic-signal", frame.frame_id, signal_type.value, polarity.value, severity_or_weight, rationale)
    return SemanticSignal(
        signal_id=signal_id,
        frame_id=frame.frame_id,
        signal_type=signal_type,
        polarity=polarity,
        severity_or_weight=severity_or_weight,
        rationale=rationale,
        source_reference_ids=tuple(source_reference_ids),
        provenance_reference_ids=tuple(provenance_reference_ids or frame.provenance_reference_ids),
        notes=notes or "semantic signal is inert and not applied",
    )


def decide_semantic_adapter(
    unit: StructuralInputUnit,
    *,
    frames: tuple[SemanticFrame, ...] | list[SemanticFrame] = (),
    signals: tuple[SemanticSignal, ...] | list[SemanticSignal] = (),
    require_human_review: bool = False,
    force_blocked: bool = False,
) -> SemanticAdapterDecision:
    frames = tuple(frames)
    signals = tuple(signals)
    if force_blocked or any(value is True for value in RUNTIME_V14L_INVARIANT_FLAGS.values()):
        outcome = SemanticAdapterOutcome.BLOCKED_BY_INVARIANT
        rationale = "Semantic adapter is blocked by invariant."
    elif require_human_review or any(signal.signal_type == SemanticSignalType.REQUIRES_HUMAN_REVIEW for signal in signals):
        outcome = SemanticAdapterOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Semantic adapter output requires human review."
    elif any(signal.signal_type == SemanticSignalType.BLOCKED_BY_INVARIANT for signal in signals):
        outcome = SemanticAdapterOutcome.BLOCKED_BY_INVARIANT
        rationale = "Signal indicates invariant block."
    elif frames and any(signal.signal_type == SemanticSignalType.POSSIBLE_MEMORY_CANDIDATE for signal in signals):
        outcome = SemanticAdapterOutcome.ELIGIBLE_FOR_FUTURE_CANDIDATE_ENVELOPE
        rationale = "Adapter output may later become a candidate envelope; no write is performed."
    elif frames:
        outcome = SemanticAdapterOutcome.FRAME_ONLY
        rationale = "Adapter produced frame-only review material."
    elif signals:
        outcome = SemanticAdapterOutcome.SIGNAL_ONLY
        rationale = "Adapter produced signal-only review material."
    else:
        outcome = SemanticAdapterOutcome.DEFER
        rationale = "Adapter needs more structure."
    decision_id = _stable_id("semantic-adapter-decision", unit.unit_id, tuple(frame.frame_id for frame in frames), tuple(signal.signal_id for signal in signals), outcome.value)
    return SemanticAdapterDecision(
        decision_id=decision_id,
        unit_id=unit.unit_id,
        frame_ids=tuple(frame.frame_id for frame in frames),
        signal_ids=tuple(signal.signal_id for signal in signals),
        outcome=outcome,
        rationale=rationale,
        notes="decision is review-only; no adapter output is applied",
    )


def create_semantic_adapter_trace(
    *,
    unit: StructuralInputUnit,
    frames: tuple[SemanticFrame, ...] | list[SemanticFrame] = (),
    role_assignments: tuple[SemanticRoleAssignment, ...] | list[SemanticRoleAssignment] = (),
    signals: tuple[SemanticSignal, ...] | list[SemanticSignal] = (),
    decision: SemanticAdapterDecision | None = None,
    notes: str = "",
) -> SemanticAdapterTrace:
    frame_ids = tuple(sorted(frame.frame_id for frame in frames))
    role_ids = tuple(sorted(role.assignment_id for role in role_assignments))
    signal_ids = tuple(sorted(signal.signal_id for signal in signals))
    decision_id = decision.decision_id if decision else ""
    trace_id = _stable_id("semantic-adapter-trace", unit.unit_id, frame_ids, role_ids, signal_ids, decision_id)
    return SemanticAdapterTrace(
        trace_id=trace_id,
        unit_id=unit.unit_id,
        frame_ids=frame_ids,
        role_assignment_ids=role_ids,
        signal_ids=signal_ids,
        decision_id=decision_id,
        source_reference_ids=(unit.source_reference_id,),
        notes=notes or "trace is generated for review only and is not applied",
    )


def create_semantic_adapter_plan(
    *,
    units: tuple[StructuralInputUnit, ...] | list[StructuralInputUnit] = (),
    frames: tuple[SemanticFrame, ...] | list[SemanticFrame] = (),
    decisions: tuple[SemanticAdapterDecision, ...] | list[SemanticAdapterDecision] = (),
    notes: str = "",
) -> SemanticAdapterPlan:
    unit_ids = tuple(sorted(unit.unit_id for unit in units))
    frame_ids = tuple(sorted(frame.frame_id for frame in frames))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    plan_id = _stable_id("semantic-adapter-plan", unit_ids, frame_ids, decision_ids)
    return SemanticAdapterPlan(
        plan_id=plan_id,
        unit_ids=unit_ids,
        frame_ids=frame_ids,
        decision_ids=decision_ids,
        notes=notes or "semantic adapter plan is design-only; it cannot write or schedule work",
    )


def create_semantic_adapter_report_entry(
    *,
    trace: SemanticAdapterTrace,
    frames: tuple[SemanticFrame, ...] | list[SemanticFrame] = (),
    role_assignments: tuple[SemanticRoleAssignment, ...] | list[SemanticRoleAssignment] = (),
    signals: tuple[SemanticSignal, ...] | list[SemanticSignal] = (),
    decision: SemanticAdapterDecision | None = None,
    unresolved_gaps: tuple[str, ...] | list[str] = (),
    recommended_next_review_step: str = "raw input / experience adapter design",
    notes: str = "",
) -> SemanticAdapterReportEntry:
    frame_summary = f"{len(tuple(frames))} frame(s), none canonical or learned"
    role_summary = f"{len(tuple(role_assignments))} role assignment(s), none authoritative"
    signal_summary = f"{len(tuple(signals))} signal(s), none active or applied"
    decision_summary = decision.outcome.value if decision else "no decision"
    report_entry_id = _stable_id("semantic-adapter-report-entry", trace.trace_id, frame_summary, role_summary, signal_summary, decision_summary)
    return SemanticAdapterReportEntry(
        report_entry_id=report_entry_id,
        trace_id=trace.trace_id,
        unit_id=trace.unit_id,
        frame_summary=frame_summary,
        role_summary=role_summary,
        signal_summary=signal_summary,
        decision_summary=decision_summary,
        unresolved_gaps=tuple(unresolved_gaps),
        recommended_next_review_step=recommended_next_review_step,
        notes=notes or "report entry is review-only; no runtime state is mutated",
    )


def validate_structural_input_unit_inert(unit: StructuralInputUnit) -> bool:
    return unit.active is False and unit.memory is False and unit.training_example is False


def validate_semantic_frame_inert(frame: SemanticFrame) -> bool:
    return frame.active is False and frame.canonical is False and frame.learned is False


def validate_semantic_role_assignment_non_authoritative(role: SemanticRoleAssignment) -> bool:
    return role.authoritative is False and role.applied is False


def validate_semantic_signal_inert(signal: SemanticSignal) -> bool:
    return signal.active is False and signal.applied is False


def validate_semantic_adapter_decision_review_only(decision: SemanticAdapterDecision) -> bool:
    return (
        decision.applied is False
        and decision.memory_written is False
        and decision.training_triggered is False
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_semantic_adapter_trace_review_only(trace: SemanticAdapterTrace) -> bool:
    return trace.generated_for_review_only is True and trace.applied is False


def validate_semantic_adapter_plan_inert(plan: SemanticAdapterPlan) -> bool:
    return (
        plan.semantic_adapter_enabled is False
        and plan.live_adaptation_enabled is False
        and plan.candidate_envelope_write_enabled is False
        and plan.canonical_write_enabled is False
        and plan.active_store_enabled is False
        and plan.memory_mutation_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.training_enabled is False
        and plan.provider_calls_enabled is False
        and plan.specialist_routing_enabled is False
        and plan.scheduler_enabled is False
        and plan.execution_enabled is False
        and plan.runtime_defaults_changed is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_semantic_adapter_report_entry_review_only(entry: SemanticAdapterReportEntry) -> bool:
    return entry.generated_for_review_only is True


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


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
