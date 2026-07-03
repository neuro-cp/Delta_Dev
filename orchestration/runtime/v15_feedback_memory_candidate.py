from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V15G_FEEDBACK_MEMORY_CANDIDATE_FLAGS: dict[str, bool] = {
    "feedback_memory_candidate_enabled": True,
    "review_only_candidate_generation_enabled": True,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "memory_mutation_enabled": False,
    "canonical_write_enabled": False,
    "canonical_write_performed": False,
    "runtime_recall_mutation_enabled": False,
    "training_enabled": False,
    "dataset_export_enabled": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
    "scheduler_enabled": False,
    "background_listener_enabled": False,
    "runtime_defaults_changed": False,
}


class FeedbackSignalType(str, Enum):
    CONFIRMATION = "confirmation"
    CORRECTION = "correction"
    REJECTION = "rejection"
    AMBIGUITY = "ambiguity"
    SARCASM_POSSIBLE = "sarcasm_possible"
    UNKNOWN = "unknown"


class MemoryCandidateSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    AMBIGUITY_REVIEW_REQUIRED = "ambiguity_review_required"
    SARCASM_REVIEW_REQUIRED = "sarcasm_review_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT = "reject"


class MemoryCandidateOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    CANDIDATE_ONLY = "candidate_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_MORE_EVIDENCE = "requires_more_evidence"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_HUMAN_APPROVED_WRITE_TRIAL = "eligible_for_future_human_approved_write_trial"


@dataclass(frozen=True)
class FeedbackInteractionInput:
    interaction_id: str
    original_question: str
    original_answer_summary: str
    user_feedback: str
    source: str = "manual_console"
    one_shot: bool = True
    auto_ingest: bool = False
    training_example: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class FeedbackSignalPreview:
    feedback_signal_id: str
    interaction_id: str
    signal_type: FeedbackSignalType
    signal_summary: str
    confidence_label: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class MemoryCandidateProposal:
    memory_candidate_id: str
    feedback_signal_id: str
    proposed_memory_text: str
    scope: str
    provenance_reference_ids: tuple[str, ...]
    human_approval_required: bool = True
    canonical_write_ready: bool = False
    approved: bool = False
    written: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class MemoryCandidateSafetyReview:
    review_id: str
    memory_candidate_id: str
    safety_status: MemoryCandidateSafetyStatus
    risk_notes: tuple[str, ...]
    ambiguity_notes: tuple[str, ...]
    sarcasm_notes: tuple[str, ...]
    required_before_write: bool = True
    approved: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class MemoryCandidateApprovalRequirement:
    requirement_id: str
    memory_candidate_id: str
    required_actor: str
    approval_reason: str
    satisfied: bool = False
    approval_present: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class MemoryCandidateDecision:
    decision_id: str
    memory_candidate_id: str
    outcome: MemoryCandidateOutcome
    rationale: str
    applied: bool = False
    canonical_write_triggered: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class MemoryCandidateAuditRecord:
    audit_id: str
    memory_candidate_id: str
    feedback_signal_id: str
    decision_id: str
    audit_summary: str
    generated_for_review_only: bool = True
    persisted_to_canonical_store: bool = False
    memory_written: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class MemoryCandidateReportEntry:
    report_entry_id: str
    memory_candidate_id: str
    feedback_summary: str
    proposal_summary: str
    safety_summary: str
    approval_summary: str
    decision_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_feedback_interaction_input(original_question: str, original_answer_summary: str, user_feedback: str) -> FeedbackInteractionInput:
    question = " ".join(original_question.split())
    answer = " ".join(original_answer_summary.split())
    feedback = " ".join(user_feedback.split())
    return FeedbackInteractionInput(
        interaction_id=_stable_id("feedback-interaction", question, answer, feedback),
        original_question=question,
        original_answer_summary=answer,
        user_feedback=feedback,
    )


def create_feedback_signal_preview(interaction: FeedbackInteractionInput) -> FeedbackSignalPreview:
    lowered = interaction.user_feedback.lower()
    if any(token in lowered for token in ("yeah sure", "whatever", "sure whatever")):
        signal_type = FeedbackSignalType.SARCASM_POSSIBLE
        confidence = "low_sarcasm_possible"
    elif lowered.startswith("no") or "not active" in lowered or "wrong" in lowered or "actually" in lowered:
        signal_type = FeedbackSignalType.CORRECTION
        confidence = "local_correction_signal"
    elif any(token in lowered for token in ("that is right", "that's right", "correct", "yes", "yeah")):
        signal_type = FeedbackSignalType.CONFIRMATION
        confidence = "local_confirmation_signal"
    elif any(token in lowered for token in ("unclear", "maybe", "ambiguous")):
        signal_type = FeedbackSignalType.AMBIGUITY
        confidence = "low_ambiguous"
    elif "reject" in lowered or "false" in lowered:
        signal_type = FeedbackSignalType.REJECTION
        confidence = "local_rejection_signal"
    else:
        signal_type = FeedbackSignalType.UNKNOWN
        confidence = "unsupported"
    return FeedbackSignalPreview(
        feedback_signal_id=_stable_id("feedback-signal", interaction.interaction_id, signal_type.value, interaction.user_feedback),
        interaction_id=interaction.interaction_id,
        signal_type=signal_type,
        signal_summary=interaction.user_feedback,
        confidence_label=confidence,
    )


def create_memory_candidate_proposal(interaction: FeedbackInteractionInput, signal: FeedbackSignalPreview) -> MemoryCandidateProposal:
    if signal.signal_type in {FeedbackSignalType.CONFIRMATION, FeedbackSignalType.CORRECTION}:
        text = _proposal_text(interaction, signal)
    else:
        text = "No memory candidate should be written from ambiguous, sarcastic, rejected, or unknown feedback without review."
    return MemoryCandidateProposal(
        memory_candidate_id=_stable_id("memory-candidate", signal.feedback_signal_id, text),
        feedback_signal_id=signal.feedback_signal_id,
        proposed_memory_text=text,
        scope="delta_runtime_self_knowledge_review",
        provenance_reference_ids=(interaction.interaction_id, signal.feedback_signal_id),
    )


def review_memory_candidate(signal: FeedbackSignalPreview, proposal: MemoryCandidateProposal) -> MemoryCandidateSafetyReview:
    if signal.signal_type == FeedbackSignalType.SARCASM_POSSIBLE:
        status = MemoryCandidateSafetyStatus.SARCASM_REVIEW_REQUIRED
        ambiguity = ("sarcasm possible; do not treat as confirmation",)
        sarcasm = ("feedback contains casual/sarcastic pattern",)
    elif signal.signal_type == FeedbackSignalType.AMBIGUITY:
        status = MemoryCandidateSafetyStatus.AMBIGUITY_REVIEW_REQUIRED
        ambiguity = ("feedback is ambiguous",)
        sarcasm = ()
    elif signal.signal_type in {FeedbackSignalType.CONFIRMATION, FeedbackSignalType.CORRECTION}:
        status = MemoryCandidateSafetyStatus.HUMAN_REVIEW_REQUIRED
        ambiguity = ()
        sarcasm = ()
    elif signal.signal_type == FeedbackSignalType.REJECTION:
        status = MemoryCandidateSafetyStatus.INSUFFICIENT_EVIDENCE
        ambiguity = ("rejection alone is not enough for canonical memory",)
        sarcasm = ()
    else:
        status = MemoryCandidateSafetyStatus.INSUFFICIENT_EVIDENCE
        ambiguity = ("unknown feedback signal",)
        sarcasm = ()
    return MemoryCandidateSafetyReview(
        review_id=_stable_id("memory-candidate-review", proposal.memory_candidate_id, status.value),
        memory_candidate_id=proposal.memory_candidate_id,
        safety_status=status,
        risk_notes=("canonical write disabled", "human approval required", "feedback signal is not truth"),
        ambiguity_notes=ambiguity,
        sarcasm_notes=sarcasm,
    )


def create_memory_candidate_decision(signal: FeedbackSignalPreview, proposal: MemoryCandidateProposal, review: MemoryCandidateSafetyReview) -> MemoryCandidateDecision:
    if signal.signal_type in {FeedbackSignalType.CONFIRMATION, FeedbackSignalType.CORRECTION}:
        outcome = MemoryCandidateOutcome.ELIGIBLE_FOR_FUTURE_HUMAN_APPROVED_WRITE_TRIAL
        rationale = "Signal can create candidate pressure only; human approval and future write trial are required."
    elif review.safety_status in {MemoryCandidateSafetyStatus.SARCASM_REVIEW_REQUIRED, MemoryCandidateSafetyStatus.AMBIGUITY_REVIEW_REQUIRED}:
        outcome = MemoryCandidateOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Ambiguity/sarcasm risk blocks write readiness."
    else:
        outcome = MemoryCandidateOutcome.REQUIRES_MORE_EVIDENCE
        rationale = "Feedback is not sufficient evidence for a memory candidate."
    return MemoryCandidateDecision(
        decision_id=_stable_id("memory-candidate-decision", proposal.memory_candidate_id, outcome.value),
        memory_candidate_id=proposal.memory_candidate_id,
        outcome=outcome,
        rationale=rationale,
    )


def build_feedback_memory_candidate_case(original_question: str, original_answer_summary: str, user_feedback: str) -> dict[str, object]:
    interaction = create_feedback_interaction_input(original_question, original_answer_summary, user_feedback)
    signal = create_feedback_signal_preview(interaction)
    proposal = create_memory_candidate_proposal(interaction, signal)
    review = review_memory_candidate(signal, proposal)
    approval = MemoryCandidateApprovalRequirement(
        requirement_id=_stable_id("memory-candidate-approval", proposal.memory_candidate_id),
        memory_candidate_id=proposal.memory_candidate_id,
        required_actor="human_operator",
        approval_reason="Canonical memory writes require explicit human approval in a later write trial.",
    )
    decision = create_memory_candidate_decision(signal, proposal, review)
    audit = MemoryCandidateAuditRecord(
        audit_id=_stable_id("memory-candidate-audit", proposal.memory_candidate_id, decision.decision_id),
        memory_candidate_id=proposal.memory_candidate_id,
        feedback_signal_id=signal.feedback_signal_id,
        decision_id=decision.decision_id,
        audit_summary="Review-only memory candidate proposal; no canonical write, recall mutation, or training occurred.",
    )
    entry = MemoryCandidateReportEntry(
        report_entry_id=_stable_id("memory-candidate-entry", proposal.memory_candidate_id),
        memory_candidate_id=proposal.memory_candidate_id,
        feedback_summary=f"{signal.signal_type.value}: {signal.signal_summary}",
        proposal_summary=proposal.proposed_memory_text,
        safety_summary=review.safety_status.value,
        approval_summary="human approval required and absent by default",
        decision_summary=decision.outcome.value,
        unresolved_gaps=("human approval absent", "canonical write disabled", "recall mutation disabled"),
        recommended_next_review_step="V1.5H human-approved canonical memory write trial design",
    )
    return {
        "interaction": interaction.as_dict(),
        "feedback_signal": signal.as_dict(),
        "memory_candidate": proposal.as_dict(),
        "safety_review": review.as_dict(),
        "approval_requirement": approval.as_dict(),
        "decision": decision.as_dict(),
        "audit_record": audit.as_dict(),
        "report_entry": entry.as_dict(),
        "invariant_flags": dict(RUNTIME_V15G_FEEDBACK_MEMORY_CANDIDATE_FLAGS),
    }


def validate_feedback_memory_candidate_safe(case: dict[str, object]) -> bool:
    proposal = case["memory_candidate"]
    approval = case["approval_requirement"]
    decision = case["decision"]
    audit = case["audit_record"]
    flags = case["invariant_flags"]
    return (
        proposal["human_approval_required"] is True
        and proposal["canonical_write_ready"] is False
        and proposal["approved"] is False
        and proposal["written"] is False
        and approval["satisfied"] is False
        and approval["approval_present"] is False
        and decision["applied"] is False
        and decision["canonical_write_triggered"] is False
        and decision["training_triggered"] is False
        and audit["persisted_to_canonical_store"] is False
        and audit["memory_written"] is False
        and audit["training_triggered"] is False
        and flags["feedback_memory_candidate_enabled"] is True
        and flags["review_only_candidate_generation_enabled"] is True
        and all(value is False for key, value in flags.items() if key not in {"feedback_memory_candidate_enabled", "review_only_candidate_generation_enabled"})
    )


def sample_feedback_memory_candidate_cases() -> tuple[dict[str, object], ...]:
    return (
        build_feedback_memory_candidate_case(
            "What is HYB1?",
            "HYB1 is dormant/env-gated and Model B remains default.",
            "Yeah, that is right. HYB1 reduced reasoning drift in the V1.4U snapshot.",
        ),
        build_feedback_memory_candidate_case(
            "What is HYB1?",
            "HYB1 is active.",
            "No, HYB1 is not active. It is dormant and env-gated.",
        ),
        build_feedback_memory_candidate_case(
            "What is HYB1?",
            "HYB1 is dormant/env-gated and Model B remains default.",
            "Yeah sure, whatever.",
        ),
    )


def _proposal_text(interaction: FeedbackInteractionInput, signal: FeedbackSignalPreview) -> str:
    if signal.signal_type == FeedbackSignalType.CORRECTION:
        return f"Review candidate from correction: {interaction.user_feedback}"
    return f"Review candidate from confirmation: {interaction.user_feedback}"


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
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
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)
