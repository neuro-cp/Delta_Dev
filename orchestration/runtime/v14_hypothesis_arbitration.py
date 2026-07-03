from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14I_INVARIANT_FLAGS: dict[str, bool] = {
    "arbitration_authority_enabled": False,
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
    "runtime_defaults_changed": False,
}


class HypothesisType(str, Enum):
    INTERPRETATION = "interpretation"
    CORRECTION = "correction"
    MEMORY_CANDIDATE = "memory_candidate"
    CONSOLIDATION_CANDIDATE = "consolidation_candidate"
    LEARNING_CANDIDATE = "learning_candidate"
    SAFETY_HYPOTHESIS = "safety_hypothesis"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    SPECIALIST_EVIDENCE_CANDIDATE = "specialist_evidence_candidate"


class HypothesisEvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    WEAKLY_SUPPORTS = "weakly_supports"
    CONTRADICTS = "contradicts"
    WEAKLY_CONTRADICTS = "weakly_contradicts"
    MISSING = "missing"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


class HypothesisConflictType(str, Enum):
    DIRECT_CONTRADICTION = "direct_contradiction"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    STALE_VS_RECENT = "stale_vs_recent"
    SAFETY_CONFLICT = "safety_conflict"
    PROVENANCE_CONFLICT = "provenance_conflict"
    LANE_SCOPE_CONFLICT = "lane_scope_conflict"
    CANONICAL_CONFLICT = "canonical_conflict"
    LEARNING_CONFLICT = "learning_conflict"


class HypothesisArbitrationOutcome(str, Enum):
    UNRESOLVED = "unresolved"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICT_REQUIRES_REPLAY = "conflict_requires_replay"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REPORT_PREFERRED_HYPOTHESIS = "report_preferred_hypothesis"
    REJECT_HYPOTHESIS = "reject_hypothesis"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_SPECIALIST_EVIDENCE = "eligible_for_future_specialist_evidence"
    ELIGIBLE_FOR_FUTURE_LEARNING_REVIEW = "eligible_for_future_learning_review"


class HypothesisEscalationType(str, Enum):
    REPLAY_REVIEW = "replay_review"
    HUMAN_REVIEW = "human_review"
    SPECIALIST_EVIDENCE_REQUEST = "specialist_evidence_request"
    CONTROLLED_LEARNING_REVIEW = "controlled_learning_review"
    CANONICAL_STORE_REVIEW = "canonical_store_review"
    REJECT_NO_ACTION = "reject_no_action"


@dataclass(frozen=True)
class HypothesisClaim:
    hypothesis_id: str
    claim_text: str
    hypothesis_type: HypothesisType
    source_reference_ids: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    confidence_state: float = 0.0
    provenance_notes: str = ""
    active: bool = False
    canonical: bool = False
    learned: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence_state)))

    def as_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "claim_text": self.claim_text,
            "hypothesis_type": self.hypothesis_type.value,
            "source_reference_ids": list(self.source_reference_ids),
            "lane_scope": list(self.lane_scope),
            "confidence_state": self.normalized_confidence(),
            "provenance_notes": self.provenance_notes,
            "active": self.active,
            "canonical": self.canonical,
            "learned": self.learned,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisEvidenceLink:
    link_id: str
    hypothesis_id: str
    source_reference_id: str
    evidence_relation: HypothesisEvidenceRelation
    evidence_weight: float = 0.0
    rationale: str = ""
    provenance_reference_ids: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_weight(self) -> float:
        return max(0.0, min(1.0, float(self.evidence_weight)))

    def as_dict(self) -> dict[str, object]:
        return {
            "link_id": self.link_id,
            "hypothesis_id": self.hypothesis_id,
            "source_reference_id": self.source_reference_id,
            "evidence_relation": self.evidence_relation.value,
            "evidence_weight": self.normalized_weight(),
            "rationale": self.rationale,
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisConflict:
    conflict_id: str
    hypothesis_ids: tuple[str, ...]
    conflict_type: HypothesisConflictType
    rationale: str = ""
    source_reference_ids: tuple[str, ...] = ()
    requires_replay_review: bool = False
    requires_human_review: bool = False
    resolved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "conflict_id": self.conflict_id,
            "hypothesis_ids": list(self.hypothesis_ids),
            "conflict_type": self.conflict_type.value,
            "rationale": self.rationale,
            "source_reference_ids": list(self.source_reference_ids),
            "requires_replay_review": self.requires_replay_review,
            "requires_human_review": self.requires_human_review,
            "resolved": self.resolved,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisArbitrationInput:
    arbitration_input_id: str
    hypotheses: tuple[HypothesisClaim, ...]
    evidence_links: tuple[HypothesisEvidenceLink, ...] = ()
    conflicts: tuple[HypothesisConflict, ...] = ()
    source_artifact_references: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    provider_calls_enabled: bool = False
    specialist_routing_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "arbitration_input_id": self.arbitration_input_id,
            "hypotheses": [hypothesis.as_dict() for hypothesis in self.hypotheses],
            "evidence_links": [link.as_dict() for link in self.evidence_links],
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
            "source_artifact_references": list(self.source_artifact_references),
            "lane_scope": list(self.lane_scope),
            "provider_calls_enabled": self.provider_calls_enabled,
            "specialist_routing_enabled": self.specialist_routing_enabled,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisScorecard:
    scorecard_id: str
    hypothesis_id: str
    support_score: float = 0.0
    contradiction_score: float = 0.0
    provenance_score: float = 0.0
    safety_score: float = 1.0
    uncertainty_score: float = 0.0
    overall_rank_score: float = 0.0
    rationale: str = ""
    score_is_authoritative: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "scorecard_id": self.scorecard_id,
            "hypothesis_id": self.hypothesis_id,
            "support_score": _clamp(self.support_score),
            "contradiction_score": _clamp(self.contradiction_score),
            "provenance_score": _clamp(self.provenance_score),
            "safety_score": _clamp(self.safety_score),
            "uncertainty_score": _clamp(self.uncertainty_score),
            "overall_rank_score": _clamp(self.overall_rank_score),
            "rationale": self.rationale,
            "score_is_authoritative": self.score_is_authoritative,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisArbitrationDecision:
    decision_id: str
    arbitration_input_id: str
    outcome: HypothesisArbitrationOutcome
    preferred_hypothesis_id: str = ""
    rejected_hypothesis_ids: tuple[str, ...] = ()
    rationale: str = ""
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14I_INVARIANT_FLAGS))
    applied: bool = False
    authoritative: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "arbitration_input_id": self.arbitration_input_id,
            "outcome": self.outcome.value,
            "preferred_hypothesis_id": self.preferred_hypothesis_id,
            "rejected_hypothesis_ids": list(self.rejected_hypothesis_ids),
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "authoritative": self.authoritative,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisArbitrationReport:
    report_id: str
    input_id: str
    scorecards: tuple[HypothesisScorecard, ...]
    decision: HypothesisArbitrationDecision
    unresolved_conflicts: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    recommended_next_review_step: str = ""
    generated_for_review_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "input_id": self.input_id,
            "scorecards": [scorecard.as_dict() for scorecard in self.scorecards],
            "decision": self.decision.as_dict(),
            "unresolved_conflicts": list(self.unresolved_conflicts),
            "evidence_gaps": list(self.evidence_gaps),
            "recommended_next_review_step": self.recommended_next_review_step,
            "generated_for_review_only": self.generated_for_review_only,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisArbitrationPlan:
    plan_id: str
    arbitration_input_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    arbitration_authority_enabled: bool = False
    canonical_write_enabled: bool = False
    active_store_enabled: bool = False
    memory_mutation_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    training_enabled: bool = False
    fine_tuning_enabled: bool = False
    pruning_enabled: bool = False
    projection_application_enabled: bool = False
    provider_calls_enabled: bool = False
    specialist_routing_enabled: bool = False
    scheduler_enabled: bool = False
    runtime_defaults_changed: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14I_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "arbitration_input_ids": list(self.arbitration_input_ids),
            "decision_ids": list(self.decision_ids),
            "arbitration_authority_enabled": self.arbitration_authority_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "active_store_enabled": self.active_store_enabled,
            "memory_mutation_enabled": self.memory_mutation_enabled,
            "runtime_recall_mutation_enabled": self.runtime_recall_mutation_enabled,
            "training_enabled": self.training_enabled,
            "fine_tuning_enabled": self.fine_tuning_enabled,
            "pruning_enabled": self.pruning_enabled,
            "projection_application_enabled": self.projection_application_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "specialist_routing_enabled": self.specialist_routing_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HypothesisReviewEscalation:
    escalation_id: str
    arbitration_decision_id: str
    escalation_type: HypothesisEscalationType
    rationale: str = ""
    required_evidence_or_approval: tuple[str, ...] = ()
    target_review_layer: str = ""
    triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "escalation_id": self.escalation_id,
            "arbitration_decision_id": self.arbitration_decision_id,
            "escalation_type": self.escalation_type.value,
            "rationale": self.rationale,
            "required_evidence_or_approval": list(self.required_evidence_or_approval),
            "target_review_layer": self.target_review_layer,
            "triggered": self.triggered,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_hypothesis_claim(
    *,
    claim_text: str,
    hypothesis_type: HypothesisType,
    source_reference_ids: tuple[str, ...] = (),
    lane_scope: tuple[str, ...] = (),
    confidence_state: float = 0.0,
    provenance_notes: str = "",
) -> HypothesisClaim:
    refs = tuple(sorted(source_reference_ids))
    lanes = tuple(sorted(lane_scope))
    return HypothesisClaim(
        hypothesis_id=_stable_id("hypothesis", (claim_text, hypothesis_type.value, *refs, *lanes)),
        claim_text=claim_text,
        hypothesis_type=hypothesis_type,
        source_reference_ids=refs,
        lane_scope=lanes,
        confidence_state=confidence_state,
        provenance_notes=provenance_notes,
        notes="hypothesis claim only; not canonical, active, or learned",
    )


def create_hypothesis_evidence_link(
    *,
    hypothesis_id: str,
    source_reference_id: str,
    evidence_relation: HypothesisEvidenceRelation,
    evidence_weight: float = 0.0,
    rationale: str = "",
    provenance_reference_ids: tuple[str, ...] = (),
) -> HypothesisEvidenceLink:
    refs = tuple(sorted(provenance_reference_ids))
    return HypothesisEvidenceLink(
        link_id=_stable_id("hypothesis-link", (hypothesis_id, source_reference_id, evidence_relation.value, *refs, rationale)),
        hypothesis_id=hypothesis_id,
        source_reference_id=source_reference_id,
        evidence_relation=evidence_relation,
        evidence_weight=evidence_weight,
        rationale=rationale,
        provenance_reference_ids=refs,
        notes="evidence link only; source evidence is not mutated",
    )


def create_hypothesis_conflict(
    *,
    hypothesis_ids: tuple[str, ...],
    conflict_type: HypothesisConflictType,
    rationale: str = "",
    source_reference_ids: tuple[str, ...] = (),
    requires_replay_review: bool = False,
    requires_human_review: bool = False,
) -> HypothesisConflict:
    ids = tuple(sorted(hypothesis_ids))
    refs = tuple(sorted(source_reference_ids))
    return HypothesisConflict(
        conflict_id=_stable_id("hypothesis-conflict", (*ids, conflict_type.value, *refs, rationale)),
        hypothesis_ids=ids,
        conflict_type=conflict_type,
        rationale=rationale,
        source_reference_ids=refs,
        requires_replay_review=requires_replay_review,
        requires_human_review=requires_human_review,
        notes="conflict is unresolved report material; it does not assign truth",
    )


def create_hypothesis_arbitration_input(
    *,
    hypotheses: tuple[HypothesisClaim, ...] | list[HypothesisClaim],
    evidence_links: tuple[HypothesisEvidenceLink, ...] | list[HypothesisEvidenceLink] = (),
    conflicts: tuple[HypothesisConflict, ...] | list[HypothesisConflict] = (),
    source_artifact_references: tuple[str, ...] = (),
    lane_scope: tuple[str, ...] = (),
) -> HypothesisArbitrationInput:
    ordered_hypotheses = tuple(sorted(hypotheses, key=lambda hypothesis: hypothesis.hypothesis_id))
    ordered_links = tuple(sorted(evidence_links, key=lambda link: link.link_id))
    ordered_conflicts = tuple(sorted(conflicts, key=lambda conflict: conflict.conflict_id))
    refs = tuple(sorted(source_artifact_references))
    lanes = tuple(sorted(lane_scope))
    return HypothesisArbitrationInput(
        arbitration_input_id=_stable_id(
            "hypothesis-arbitration-input",
            (
                *[hypothesis.hypothesis_id for hypothesis in ordered_hypotheses],
                *[link.link_id for link in ordered_links],
                *[conflict.conflict_id for conflict in ordered_conflicts],
                *refs,
                *lanes,
            ),
        ),
        hypotheses=ordered_hypotheses,
        evidence_links=ordered_links,
        conflicts=ordered_conflicts,
        source_artifact_references=refs,
        lane_scope=lanes,
        notes="arbitration input is local and report-only; no provider or specialist route is triggered",
    )


def score_hypotheses(arbitration_input: HypothesisArbitrationInput) -> tuple[HypothesisScorecard, ...]:
    scorecards: list[HypothesisScorecard] = []
    for hypothesis in arbitration_input.hypotheses:
        links = tuple(link for link in arbitration_input.evidence_links if link.hypothesis_id == hypothesis.hypothesis_id)
        conflicts = tuple(
            conflict for conflict in arbitration_input.conflicts if hypothesis.hypothesis_id in conflict.hypothesis_ids
        )
        support = _support_score(links)
        contradiction = _contradiction_score(links, conflicts)
        provenance = _provenance_score(hypothesis, links)
        safety = _safety_score(links, conflicts)
        uncertainty = _uncertainty_score(links, conflicts)
        overall = _clamp((0.4 * support) + (0.2 * provenance) + (0.2 * safety) - (0.25 * contradiction) - (0.15 * uncertainty))
        scorecards.append(
            HypothesisScorecard(
                scorecard_id=_stable_id("hypothesis-scorecard", (arbitration_input.arbitration_input_id, hypothesis.hypothesis_id)),
                hypothesis_id=hypothesis.hypothesis_id,
                support_score=support,
                contradiction_score=contradiction,
                provenance_score=provenance,
                safety_score=safety,
                uncertainty_score=uncertainty,
                overall_rank_score=overall,
                rationale="deterministic report-only rank; not truth and not canonical memory",
                notes="score is not written to active memory",
            )
        )
    return tuple(scorecards)


def decide_hypothesis_arbitration(
    arbitration_input: HypothesisArbitrationInput,
    scorecards: tuple[HypothesisScorecard, ...] | list[HypothesisScorecard],
    *,
    force_human_review: bool = False,
    force_blocked: bool = False,
    future_specialist_evidence: bool = False,
    future_learning_review: bool = False,
) -> HypothesisArbitrationDecision:
    ordered_scorecards = tuple(sorted(scorecards, key=lambda scorecard: (-scorecard.overall_rank_score, scorecard.hypothesis_id)))
    unresolved_conflicts = [conflict for conflict in arbitration_input.conflicts if not conflict.resolved]
    if force_blocked or any(value is True for value in RUNTIME_V14I_INVARIANT_FLAGS.values()):
        outcome = HypothesisArbitrationOutcome.BLOCKED_BY_INVARIANT
        preferred = ""
        rationale = "A V1.4I invariant blocks arbitration authority."
    elif force_human_review or any(conflict.requires_human_review for conflict in unresolved_conflicts):
        outcome = HypothesisArbitrationOutcome.REQUIRES_HUMAN_REVIEW
        preferred = ""
        rationale = "Human review is required before any future interpretation."
    elif any(conflict.requires_replay_review for conflict in unresolved_conflicts):
        outcome = HypothesisArbitrationOutcome.CONFLICT_REQUIRES_REPLAY
        preferred = ""
        rationale = "Conflict requires replay/consolidation review."
    elif future_specialist_evidence:
        outcome = HypothesisArbitrationOutcome.ELIGIBLE_FOR_FUTURE_SPECIALIST_EVIDENCE
        preferred = ""
        rationale = "Specialist evidence may be useful later, but no route is triggered."
    elif future_learning_review:
        outcome = HypothesisArbitrationOutcome.ELIGIBLE_FOR_FUTURE_LEARNING_REVIEW
        preferred = ""
        rationale = "Hypothesis may be examined by future controlled-learning review only."
    elif not ordered_scorecards:
        outcome = HypothesisArbitrationOutcome.INSUFFICIENT_EVIDENCE
        preferred = ""
        rationale = "No hypotheses were available for report-only arbitration."
    elif ordered_scorecards[0].overall_rank_score < 0.25:
        outcome = HypothesisArbitrationOutcome.INSUFFICIENT_EVIDENCE
        preferred = ""
        rationale = "No hypothesis has enough support for report preference."
    else:
        outcome = HypothesisArbitrationOutcome.REPORT_PREFERRED_HYPOTHESIS
        preferred = ordered_scorecards[0].hypothesis_id
        rationale = "A hypothesis is report-preferred only; this is not truth, authority, or canonical memory."
    rejected = tuple(scorecard.hypothesis_id for scorecard in ordered_scorecards[1:] if scorecard.overall_rank_score < 0.2)
    return HypothesisArbitrationDecision(
        decision_id=_stable_id(
            "hypothesis-arbitration-decision",
            (arbitration_input.arbitration_input_id, outcome.value, preferred, *rejected),
        ),
        arbitration_input_id=arbitration_input.arbitration_input_id,
        outcome=outcome,
        preferred_hypothesis_id=preferred,
        rejected_hypothesis_ids=rejected,
        rationale=rationale,
        notes="decision is report-only; applied and authoritative remain false",
    )


def create_hypothesis_arbitration_report(
    arbitration_input: HypothesisArbitrationInput,
    scorecards: tuple[HypothesisScorecard, ...] | list[HypothesisScorecard],
    decision: HypothesisArbitrationDecision,
) -> HypothesisArbitrationReport:
    unresolved = tuple(conflict.conflict_id for conflict in arbitration_input.conflicts if not conflict.resolved)
    gaps = tuple(
        link.link_id
        for link in arbitration_input.evidence_links
        if link.evidence_relation == HypothesisEvidenceRelation.MISSING
    )
    return HypothesisArbitrationReport(
        report_id=_stable_id("hypothesis-arbitration-report", (arbitration_input.arbitration_input_id, decision.decision_id)),
        input_id=arbitration_input.arbitration_input_id,
        scorecards=tuple(sorted(scorecards, key=lambda scorecard: scorecard.scorecard_id)),
        decision=decision,
        unresolved_conflicts=unresolved,
        evidence_gaps=gaps,
        recommended_next_review_step=_next_review_step(decision),
        notes="generated for review only; no state is mutated",
    )


def create_hypothesis_arbitration_plan(
    *,
    inputs: tuple[HypothesisArbitrationInput, ...] | list[HypothesisArbitrationInput] = (),
    decisions: tuple[HypothesisArbitrationDecision, ...] | list[HypothesisArbitrationDecision] = (),
    notes: str = "",
) -> HypothesisArbitrationPlan:
    input_ids = tuple(sorted(item.arbitration_input_id for item in inputs))
    decision_ids = tuple(sorted(decision.decision_id for decision in decisions))
    return HypothesisArbitrationPlan(
        plan_id=_stable_id("hypothesis-arbitration-plan", (*input_ids, *decision_ids)),
        arbitration_input_ids=input_ids,
        decision_ids=decision_ids,
        notes=notes or "plan is report-only; it cannot execute, route, schedule, or mutate memory",
    )


def create_hypothesis_review_escalation(
    decision: HypothesisArbitrationDecision,
    *,
    escalation_type: HypothesisEscalationType,
    rationale: str = "",
    required_evidence_or_approval: tuple[str, ...] = (),
    target_review_layer: str = "",
) -> HypothesisReviewEscalation:
    approvals = tuple(sorted(required_evidence_or_approval))
    return HypothesisReviewEscalation(
        escalation_id=_stable_id("hypothesis-escalation", (decision.decision_id, escalation_type.value, *approvals, target_review_layer)),
        arbitration_decision_id=decision.decision_id,
        escalation_type=escalation_type,
        rationale=rationale or decision.rationale,
        required_evidence_or_approval=approvals,
        target_review_layer=target_review_layer,
        notes="escalation is not triggered in V1.4I",
    )


def validate_hypothesis_claim_inert(hypothesis: HypothesisClaim) -> bool:
    return hypothesis.active is False and hypothesis.canonical is False and hypothesis.learned is False


def validate_scorecard_report_only(scorecard: HypothesisScorecard) -> bool:
    return scorecard.score_is_authoritative is False


def validate_arbitration_input_inert(arbitration_input: HypothesisArbitrationInput) -> bool:
    return arbitration_input.provider_calls_enabled is False and arbitration_input.specialist_routing_enabled is False


def validate_arbitration_decision_report_only(decision: HypothesisArbitrationDecision) -> bool:
    return (
        decision.applied is False
        and decision.authoritative is False
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_arbitration_report_review_only(report: HypothesisArbitrationReport) -> bool:
    return report.generated_for_review_only is True and validate_arbitration_decision_report_only(report.decision)


def validate_arbitration_plan_inert(plan: HypothesisArbitrationPlan) -> bool:
    return (
        plan.arbitration_authority_enabled is False
        and plan.canonical_write_enabled is False
        and plan.active_store_enabled is False
        and plan.memory_mutation_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.training_enabled is False
        and plan.fine_tuning_enabled is False
        and plan.pruning_enabled is False
        and plan.projection_application_enabled is False
        and plan.provider_calls_enabled is False
        and plan.specialist_routing_enabled is False
        and plan.scheduler_enabled is False
        and plan.runtime_defaults_changed is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def validate_review_escalation_not_triggered(escalation: HypothesisReviewEscalation) -> bool:
    return escalation.triggered is False


def _support_score(links: tuple[HypothesisEvidenceLink, ...]) -> float:
    support = 0.0
    for link in links:
        if link.evidence_relation == HypothesisEvidenceRelation.SUPPORTS:
            support += link.normalized_weight()
        elif link.evidence_relation == HypothesisEvidenceRelation.WEAKLY_SUPPORTS:
            support += link.normalized_weight() * 0.5
    return _clamp(support)


def _contradiction_score(
    links: tuple[HypothesisEvidenceLink, ...],
    conflicts: tuple[HypothesisConflict, ...],
) -> float:
    score = 0.0
    for link in links:
        if link.evidence_relation == HypothesisEvidenceRelation.CONTRADICTS:
            score += link.normalized_weight()
        elif link.evidence_relation == HypothesisEvidenceRelation.WEAKLY_CONTRADICTS:
            score += link.normalized_weight() * 0.5
    score += 0.25 * len(conflicts)
    return _clamp(score)


def _provenance_score(hypothesis: HypothesisClaim, links: tuple[HypothesisEvidenceLink, ...]) -> float:
    refs = {ref for ref in hypothesis.source_reference_ids}
    for link in links:
        refs.update(link.provenance_reference_ids)
    return _clamp(len(refs) / 5.0)


def _safety_score(
    links: tuple[HypothesisEvidenceLink, ...],
    conflicts: tuple[HypothesisConflict, ...],
) -> float:
    if any(link.evidence_relation == HypothesisEvidenceRelation.BLOCKED_BY_INVARIANT for link in links):
        return 0.0
    if any(conflict.conflict_type == HypothesisConflictType.SAFETY_CONFLICT for conflict in conflicts):
        return 0.25
    if any(link.evidence_relation == HypothesisEvidenceRelation.REQUIRES_HUMAN_REVIEW for link in links):
        return 0.5
    return 1.0


def _uncertainty_score(
    links: tuple[HypothesisEvidenceLink, ...],
    conflicts: tuple[HypothesisConflict, ...],
) -> float:
    missing = sum(link.evidence_relation == HypothesisEvidenceRelation.MISSING for link in links)
    human = sum(link.evidence_relation == HypothesisEvidenceRelation.REQUIRES_HUMAN_REVIEW for link in links)
    return _clamp((0.25 * missing) + (0.2 * human) + (0.2 * len(conflicts)))


def _next_review_step(decision: HypothesisArbitrationDecision) -> str:
    if decision.outcome == HypothesisArbitrationOutcome.CONFLICT_REQUIRES_REPLAY:
        return "replay_review"
    if decision.outcome == HypothesisArbitrationOutcome.REQUIRES_HUMAN_REVIEW:
        return "human_review"
    if decision.outcome == HypothesisArbitrationOutcome.ELIGIBLE_FOR_FUTURE_SPECIALIST_EVIDENCE:
        return "specialist_evidence_request"
    if decision.outcome == HypothesisArbitrationOutcome.ELIGIBLE_FOR_FUTURE_LEARNING_REVIEW:
        return "controlled_learning_review"
    return "report_only_no_action"


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
