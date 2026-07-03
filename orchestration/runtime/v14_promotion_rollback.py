from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14V_INVARIANT_FLAGS: dict[str, bool] = {
    "promotion_enabled": False,
    "promotion_decision_applied": False,
    "artifact_promotion_enabled": False,
    "runtime_activation_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_remains_dormant": True,
    "model_b_default_changed": False,
    "model_default_change_enabled": False,
    "rollback_execution_enabled": False,
    "runtime_default_change_enabled": False,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "artifact_creation_enabled": False,
    "canonical_write_enabled": False,
    "memory_mutation_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
}


class PromotionCandidateType(str, Enum):
    HYB1_RUNTIME_VARIANT = "hyb1_runtime_variant"
    TRAINED_ARTIFACT_CANDIDATE = "trained_artifact_candidate"
    PROMPT_VARIANT_CANDIDATE = "prompt_variant_candidate"
    RUNTIME_CONFIG_CANDIDATE = "runtime_config_candidate"
    UNKNOWN = "unknown"


class PromotionSafetyStatus(str, Enum):
    SAFE_FOR_FUTURE_REVIEW = "safe_for_future_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNRESOLVED_REGRESSION = "unresolved_regression"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    ROLLBACK_PLAN_REQUIRED = "rollback_plan_required"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    REJECT = "reject"


class PromotionDecisionOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    KEEP_DORMANT = "keep_dormant"
    REQUIRES_MORE_EVAL = "requires_more_eval"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_ROLLBACK_PLAN = "requires_rollback_plan"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_GATED_TRIAL_DESIGN = "eligible_for_future_gated_trial_design"


class RollbackDecisionOutcome(str, Enum):
    NO_ROLLBACK_NEEDED = "no_rollback_needed"
    ROLLBACK_PLAN_REQUIRED = "rollback_plan_required"
    ROLLBACK_BLOCKED_NO_ACTIVE_CANDIDATE = "rollback_blocked_no_active_candidate"
    ROLLBACK_BLOCKED_BY_INVARIANT = "rollback_blocked_by_invariant"
    ROLLBACK_DESIGN_ONLY = "rollback_design_only"


class RuntimeDefaultChangeBlockerType(str, Enum):
    MISSING_HUMAN_REVIEW = "missing_human_review"
    MISSING_ROLLBACK_PLAN = "missing_rollback_plan"
    UNRESOLVED_REGRESSION = "unresolved_regression"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MISSING_SAFETY_REVIEW = "missing_safety_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    CANDIDATE_STILL_DORMANT = "candidate_still_dormant"


@dataclass(frozen=True)
class PromotionCandidate:
    candidate_id: str
    candidate_name: str
    candidate_type: PromotionCandidateType
    baseline_reference_id: str
    comparison_reference_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    safety_reference_ids: tuple[str, ...]
    rollback_reference_ids: tuple[str, ...]
    human_review_required: bool = True
    active: bool = False
    promoted: bool = False
    default_change_allowed: bool = False
    runtime_activation_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionEvidencePacket:
    evidence_packet_id: str
    candidate_id: str
    comparison_summary: str
    improvement_summary: str
    regression_summary: str
    safety_summary: str
    uncertainty_summary: str
    sufficient_for_review: bool
    sufficient_for_promotion: bool = False
    authoritative: bool = False
    generated_for_review_only: bool = True
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionSafetyGate:
    safety_gate_id: str
    candidate_id: str
    required_reviews: tuple[str, ...]
    invariant_failures: tuple[str, ...]
    unresolved_regressions: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    safety_status: PromotionSafetyStatus
    gate_satisfied: bool = False
    promotion_allowed: bool = False
    runtime_activation_allowed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionHumanReviewRequirement:
    review_requirement_id: str
    candidate_id: str
    required_actor: str
    review_reason: str
    required_before_trial: bool = True
    required_before_promotion: bool = True
    satisfied: bool = False
    approval_present: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionRollbackPlan:
    rollback_plan_id: str
    candidate_id: str
    baseline_reference_id: str
    rollback_strategy: str
    rollback_trigger_conditions: tuple[str, ...]
    rollback_test_required: bool = True
    rollback_ready: bool = False
    rollback_executed: bool = False
    runtime_default_restored: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionDecision:
    decision_id: str
    candidate_id: str
    outcome: PromotionDecisionOutcome
    rationale: str
    invariant_status: str
    applied: bool = False
    promoted: bool = False
    default_changed: bool = False
    runtime_activation_enabled: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class RollbackDecision:
    rollback_decision_id: str
    candidate_id: str
    rollback_plan_id: str
    outcome: RollbackDecisionOutcome
    rationale: str
    applied: bool = False
    rollback_executed: bool = False
    default_restored: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class RuntimeDefaultChangeBlocker:
    blocker_id: str
    candidate_id: str
    blocker_type: RuntimeDefaultChangeBlockerType
    rationale: str
    required_resolution: str
    resolved: bool = False
    blocks_default_change: bool = True
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionRollbackAuditRecord:
    audit_id: str
    candidate_id: str
    blocker_ids: tuple[str, ...]
    audit_summary: str
    decision_id: str = ""
    rollback_decision_id: str = ""
    evidence_packet_id: str = ""
    safety_gate_id: str = ""
    generated_for_review_only: bool = True
    persisted_to_active_registry: bool = False
    promoted: bool = False
    rollback_executed: bool = False
    default_changed: bool = False
    created_at: str = field(default_factory=lambda: _now())

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class PromotionRollbackReportEntry:
    report_entry_id: str
    candidate_id: str
    evidence_summary: str
    safety_summary: str
    human_review_summary: str
    rollback_summary: str
    blocker_summary: str
    promotion_decision_summary: str
    rollback_decision_summary: str
    unresolved_gaps: tuple[str, ...]
    recommended_next_review_step: str
    generated_for_review_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def create_promotion_candidate(
    *,
    candidate_name: str,
    candidate_type: PromotionCandidateType,
    baseline_reference_id: str,
    comparison_reference_ids: tuple[str, ...],
    evidence_reference_ids: tuple[str, ...],
    safety_reference_ids: tuple[str, ...],
    rollback_reference_ids: tuple[str, ...],
) -> PromotionCandidate:
    return PromotionCandidate(
        candidate_id=_stable_id(
            "promotion-candidate",
            candidate_name,
            candidate_type.value,
            baseline_reference_id,
            comparison_reference_ids,
            evidence_reference_ids,
            safety_reference_ids,
            rollback_reference_ids,
        ),
        candidate_name=candidate_name,
        candidate_type=candidate_type,
        baseline_reference_id=baseline_reference_id,
        comparison_reference_ids=tuple(comparison_reference_ids),
        evidence_reference_ids=tuple(evidence_reference_ids),
        safety_reference_ids=tuple(safety_reference_ids),
        rollback_reference_ids=tuple(rollback_reference_ids),
    )


def create_promotion_evidence_packet(
    *,
    candidate: PromotionCandidate,
    comparison_summary: str,
    improvement_summary: str,
    regression_summary: str,
    safety_summary: str,
    uncertainty_summary: str,
    sufficient_for_review: bool,
) -> PromotionEvidencePacket:
    return PromotionEvidencePacket(
        evidence_packet_id=_stable_id(
            "promotion-evidence",
            candidate.candidate_id,
            comparison_summary,
            improvement_summary,
            regression_summary,
            safety_summary,
            uncertainty_summary,
            sufficient_for_review,
        ),
        candidate_id=candidate.candidate_id,
        comparison_summary=comparison_summary,
        improvement_summary=improvement_summary,
        regression_summary=regression_summary,
        safety_summary=safety_summary,
        uncertainty_summary=uncertainty_summary,
        sufficient_for_review=sufficient_for_review,
    )


def create_promotion_safety_gate(
    *,
    candidate: PromotionCandidate,
    required_reviews: tuple[str, ...],
    invariant_failures: tuple[str, ...],
    unresolved_regressions: tuple[str, ...],
    missing_requirements: tuple[str, ...],
    safety_status: PromotionSafetyStatus,
) -> PromotionSafetyGate:
    return PromotionSafetyGate(
        safety_gate_id=_stable_id(
            "promotion-safety-gate",
            candidate.candidate_id,
            required_reviews,
            invariant_failures,
            unresolved_regressions,
            missing_requirements,
            safety_status.value,
        ),
        candidate_id=candidate.candidate_id,
        required_reviews=tuple(required_reviews),
        invariant_failures=tuple(invariant_failures),
        unresolved_regressions=tuple(unresolved_regressions),
        missing_requirements=tuple(missing_requirements),
        safety_status=safety_status,
    )


def create_promotion_human_review_requirement(
    *,
    candidate: PromotionCandidate,
    required_actor: str,
    review_reason: str,
) -> PromotionHumanReviewRequirement:
    return PromotionHumanReviewRequirement(
        review_requirement_id=_stable_id("promotion-human-review", candidate.candidate_id, required_actor, review_reason),
        candidate_id=candidate.candidate_id,
        required_actor=required_actor,
        review_reason=review_reason,
    )


def create_promotion_rollback_plan(
    *,
    candidate: PromotionCandidate,
    rollback_strategy: str,
    rollback_trigger_conditions: tuple[str, ...],
) -> PromotionRollbackPlan:
    return PromotionRollbackPlan(
        rollback_plan_id=_stable_id(
            "promotion-rollback-plan",
            candidate.candidate_id,
            candidate.baseline_reference_id,
            rollback_strategy,
            rollback_trigger_conditions,
        ),
        candidate_id=candidate.candidate_id,
        baseline_reference_id=candidate.baseline_reference_id,
        rollback_strategy=rollback_strategy,
        rollback_trigger_conditions=tuple(rollback_trigger_conditions),
    )


def create_promotion_decision(
    *,
    candidate: PromotionCandidate,
    outcome: PromotionDecisionOutcome,
    rationale: str,
    invariant_status: str,
) -> PromotionDecision:
    return PromotionDecision(
        decision_id=_stable_id("promotion-decision", candidate.candidate_id, outcome.value, rationale, invariant_status),
        candidate_id=candidate.candidate_id,
        outcome=outcome,
        rationale=rationale,
        invariant_status=invariant_status,
    )


def create_rollback_decision(
    *,
    candidate: PromotionCandidate,
    rollback_plan: PromotionRollbackPlan,
    outcome: RollbackDecisionOutcome,
    rationale: str,
) -> RollbackDecision:
    return RollbackDecision(
        rollback_decision_id=_stable_id("rollback-decision", candidate.candidate_id, rollback_plan.rollback_plan_id, outcome.value, rationale),
        candidate_id=candidate.candidate_id,
        rollback_plan_id=rollback_plan.rollback_plan_id,
        outcome=outcome,
        rationale=rationale,
    )


def create_runtime_default_change_blocker(
    *,
    candidate: PromotionCandidate,
    blocker_type: RuntimeDefaultChangeBlockerType,
    rationale: str,
    required_resolution: str,
) -> RuntimeDefaultChangeBlocker:
    return RuntimeDefaultChangeBlocker(
        blocker_id=_stable_id("runtime-default-blocker", candidate.candidate_id, blocker_type.value, rationale, required_resolution),
        candidate_id=candidate.candidate_id,
        blocker_type=blocker_type,
        rationale=rationale,
        required_resolution=required_resolution,
    )


def create_promotion_rollback_audit_record(
    *,
    candidate: PromotionCandidate,
    blocker_ids: tuple[str, ...],
    audit_summary: str,
    decision: PromotionDecision | None = None,
    rollback_decision: RollbackDecision | None = None,
    evidence_packet: PromotionEvidencePacket | None = None,
    safety_gate: PromotionSafetyGate | None = None,
) -> PromotionRollbackAuditRecord:
    return PromotionRollbackAuditRecord(
        audit_id=_stable_id(
            "promotion-rollback-audit",
            candidate.candidate_id,
            blocker_ids,
            audit_summary,
            decision.decision_id if decision else "",
            rollback_decision.rollback_decision_id if rollback_decision else "",
            evidence_packet.evidence_packet_id if evidence_packet else "",
            safety_gate.safety_gate_id if safety_gate else "",
        ),
        candidate_id=candidate.candidate_id,
        blocker_ids=tuple(blocker_ids),
        audit_summary=audit_summary,
        decision_id=decision.decision_id if decision else "",
        rollback_decision_id=rollback_decision.rollback_decision_id if rollback_decision else "",
        evidence_packet_id=evidence_packet.evidence_packet_id if evidence_packet else "",
        safety_gate_id=safety_gate.safety_gate_id if safety_gate else "",
    )


def create_promotion_rollback_report_entry(
    *,
    candidate: PromotionCandidate,
    evidence_summary: str,
    safety_summary: str,
    human_review_summary: str,
    rollback_summary: str,
    blocker_summary: str,
    promotion_decision_summary: str,
    rollback_decision_summary: str,
    unresolved_gaps: tuple[str, ...],
    recommended_next_review_step: str,
) -> PromotionRollbackReportEntry:
    return PromotionRollbackReportEntry(
        report_entry_id=_stable_id(
            "promotion-rollback-report-entry",
            candidate.candidate_id,
            evidence_summary,
            safety_summary,
            human_review_summary,
            rollback_summary,
            blocker_summary,
            promotion_decision_summary,
            rollback_decision_summary,
            unresolved_gaps,
            recommended_next_review_step,
        ),
        candidate_id=candidate.candidate_id,
        evidence_summary=evidence_summary,
        safety_summary=safety_summary,
        human_review_summary=human_review_summary,
        rollback_summary=rollback_summary,
        blocker_summary=blocker_summary,
        promotion_decision_summary=promotion_decision_summary,
        rollback_decision_summary=rollback_decision_summary,
        unresolved_gaps=tuple(unresolved_gaps),
        recommended_next_review_step=recommended_next_review_step,
    )


def validate_promotion_candidate_inert(candidate: PromotionCandidate) -> bool:
    return not any((candidate.active, candidate.promoted, candidate.default_change_allowed, candidate.runtime_activation_allowed))


def validate_evidence_packet_review_only(packet: PromotionEvidencePacket) -> bool:
    return packet.generated_for_review_only and not any((packet.sufficient_for_promotion, packet.authoritative))


def validate_safety_gate_closed(gate: PromotionSafetyGate) -> bool:
    return not any((gate.gate_satisfied, gate.promotion_allowed, gate.runtime_activation_allowed))


def validate_human_review_unsatisfied(requirement: PromotionHumanReviewRequirement) -> bool:
    return not any((requirement.satisfied, requirement.approval_present))


def validate_rollback_plan_inert(plan: PromotionRollbackPlan) -> bool:
    return not any((plan.rollback_ready, plan.rollback_executed, plan.runtime_default_restored))


def validate_promotion_decision_inert(decision: PromotionDecision) -> bool:
    return not any((decision.applied, decision.promoted, decision.default_changed, decision.runtime_activation_enabled))


def validate_rollback_decision_inert(decision: RollbackDecision) -> bool:
    return not any((decision.applied, decision.rollback_executed, decision.default_restored))


def validate_default_blocker_unresolved(blocker: RuntimeDefaultChangeBlocker) -> bool:
    return blocker.blocks_default_change and blocker.resolved is False


def validate_audit_record_review_only(audit: PromotionRollbackAuditRecord) -> bool:
    return audit.generated_for_review_only and not any(
        (audit.persisted_to_active_registry, audit.promoted, audit.rollback_executed, audit.default_changed)
    )


def validate_report_entry_review_only(entry: PromotionRollbackReportEntry) -> bool:
    return entry.generated_for_review_only


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
    normalized = "|".join(_normalize_part(part) for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalize_part(part: object) -> str:
    if isinstance(part, Enum):
        return part.value
    if isinstance(part, (tuple, list)):
        return "[" + ",".join(_normalize_part(item) for item in part) + "]"
    if isinstance(part, dict):
        return "{" + ",".join(f"{key}:{_normalize_part(value)}" for key, value in sorted(part.items())) + "}"
    return str(part)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
