from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


RUNTIME_V14J_INVARIANT_FLAGS: dict[str, bool] = {
    "provider_calls_enabled": False,
    "active_specialist_routing_enabled": False,
    "authority_transfer_enabled": False,
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
    "scheduler_enabled": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
    "activation_integration_enabled": False,
    "attention_integration_enabled": False,
    "runtime_defaults_changed": False,
}


class SpecialistPacketSource(str, Enum):
    MOCK_RESULT = "mock_result"
    HUMAN_PROVIDED = "human_provided"
    STORED_REPORT = "stored_report"
    FUTURE_PROVIDER_PLACEHOLDER = "future_provider_placeholder"


class SpecialistClaimType(str, Enum):
    EVIDENCE_OBSERVATION = "evidence_observation"
    INTERPRETATION = "interpretation"
    CORRECTION = "correction"
    SAFETY_NOTE = "safety_note"
    CONTRADICTION_NOTE = "contradiction_note"
    UNCERTAINTY_NOTE = "uncertainty_note"


class SpecialistEvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    WEAKLY_SUPPORTS = "weakly_supports"
    CONTRADICTS = "contradicts"
    WEAKLY_CONTRADICTS = "weakly_contradicts"
    CLARIFIES = "clarifies"
    MISSING = "missing"
    UNSAFE_TO_MERGE = "unsafe_to_merge"
    REQUIRES_REVIEW = "requires_review"


class SpecialistMergeConflictType(str, Enum):
    CLAIM_CONTRADICTION = "claim_contradiction"
    PROVENANCE_GAP = "provenance_gap"
    LANE_SCOPE_CONFLICT = "lane_scope_conflict"
    SAFETY_CONFLICT = "safety_conflict"
    AUTHORITY_RISK = "authority_risk"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CANONICAL_CONFLICT = "canonical_conflict"


class SpecialistMergeOutcome(str, Enum):
    UNRESOLVED = "unresolved"
    REPORT_ONLY_MERGE_CANDIDATE = "report_only_merge_candidate"
    DEFER_MERGE = "defer_merge"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REQUIRES_REPLAY_REVIEW = "requires_replay_review"
    REJECT_PACKET = "reject_packet"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    ELIGIBLE_FOR_FUTURE_RECALL_BRIDGE_REVIEW = "eligible_for_future_recall_bridge_review"


@dataclass(frozen=True)
class SpecialistEvidencePacket:
    packet_id: str
    specialist_name: str
    packet_source: SpecialistPacketSource
    source_reference_ids: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    summary: str = ""
    provider_call_performed: bool = False
    active_routing_used: bool = False
    authority_granted: bool = False
    canonical: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "packet_id": self.packet_id,
            "specialist_name": self.specialist_name,
            "packet_source": self.packet_source.value,
            "source_reference_ids": list(self.source_reference_ids),
            "lane_scope": list(self.lane_scope),
            "summary": self.summary,
            "provider_call_performed": self.provider_call_performed,
            "active_routing_used": self.active_routing_used,
            "authority_granted": self.authority_granted,
            "canonical": self.canonical,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistResultClaim:
    claim_id: str
    packet_id: str
    claim_text: str
    claim_type: SpecialistClaimType
    confidence_state: float = 0.0
    lane_scope: tuple[str, ...] = ()
    provenance_reference_ids: tuple[str, ...] = ()
    accepted_as_truth: bool = False
    learned: bool = False
    canonical: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return _clamp(self.confidence_state)

    def as_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "packet_id": self.packet_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "confidence_state": self.normalized_confidence(),
            "lane_scope": list(self.lane_scope),
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "accepted_as_truth": self.accepted_as_truth,
            "learned": self.learned,
            "canonical": self.canonical,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistEvidenceLink:
    link_id: str
    claim_id: str
    target_reference_id: str
    evidence_relation: SpecialistEvidenceRelation
    evidence_weight: float = 0.0
    rationale: str = ""
    provenance_reference_ids: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_weight(self) -> float:
        return _clamp(self.evidence_weight)

    def as_dict(self) -> dict[str, object]:
        return {
            "link_id": self.link_id,
            "claim_id": self.claim_id,
            "target_reference_id": self.target_reference_id,
            "evidence_relation": self.evidence_relation.value,
            "evidence_weight": self.normalized_weight(),
            "rationale": self.rationale,
            "provenance_reference_ids": list(self.provenance_reference_ids),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistMergeInput:
    merge_input_id: str
    packets: tuple[SpecialistEvidencePacket, ...]
    claims: tuple[SpecialistResultClaim, ...] = ()
    evidence_links: tuple[SpecialistEvidenceLink, ...] = ()
    source_artifact_references: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    provider_calls_enabled: bool = False
    active_specialist_routing_enabled: bool = False
    authority_transfer_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "merge_input_id": self.merge_input_id,
            "packets": [packet.as_dict() for packet in self.packets],
            "claims": [claim.as_dict() for claim in self.claims],
            "evidence_links": [link.as_dict() for link in self.evidence_links],
            "source_artifact_references": list(self.source_artifact_references),
            "lane_scope": list(self.lane_scope),
            "provider_calls_enabled": self.provider_calls_enabled,
            "active_specialist_routing_enabled": self.active_specialist_routing_enabled,
            "authority_transfer_enabled": self.authority_transfer_enabled,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistMergeConflict:
    conflict_id: str
    packet_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    conflict_type: SpecialistMergeConflictType
    rationale: str = ""
    source_reference_ids: tuple[str, ...] = ()
    requires_human_review: bool = False
    requires_replay_review: bool = False
    resolved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "conflict_id": self.conflict_id,
            "packet_ids": list(self.packet_ids),
            "claim_ids": list(self.claim_ids),
            "conflict_type": self.conflict_type.value,
            "rationale": self.rationale,
            "source_reference_ids": list(self.source_reference_ids),
            "requires_human_review": self.requires_human_review,
            "requires_replay_review": self.requires_replay_review,
            "resolved": self.resolved,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistMergeScorecard:
    scorecard_id: str
    claim_id: str
    support_score: float = 0.0
    contradiction_score: float = 0.0
    provenance_score: float = 0.0
    safety_score: float = 1.0
    merge_readiness_score: float = 0.0
    rationale: str = ""
    authoritative: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "scorecard_id": self.scorecard_id,
            "claim_id": self.claim_id,
            "support_score": _clamp(self.support_score),
            "contradiction_score": _clamp(self.contradiction_score),
            "provenance_score": _clamp(self.provenance_score),
            "safety_score": _clamp(self.safety_score),
            "merge_readiness_score": _clamp(self.merge_readiness_score),
            "rationale": self.rationale,
            "authoritative": self.authoritative,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistMergeDecision:
    decision_id: str
    merge_input_id: str
    outcome: SpecialistMergeOutcome
    merge_candidate_claim_ids: tuple[str, ...] = ()
    rejected_claim_ids: tuple[str, ...] = ()
    rationale: str = ""
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14J_INVARIANT_FLAGS))
    applied: bool = False
    authoritative: bool = False
    provider_called: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "merge_input_id": self.merge_input_id,
            "outcome": self.outcome.value,
            "merge_candidate_claim_ids": list(self.merge_candidate_claim_ids),
            "rejected_claim_ids": list(self.rejected_claim_ids),
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "authoritative": self.authoritative,
            "provider_called": self.provider_called,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistMergeReport:
    report_id: str
    merge_input_id: str
    scorecards: tuple[SpecialistMergeScorecard, ...]
    decision: SpecialistMergeDecision
    conflicts: tuple[SpecialistMergeConflict, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    generated_for_review_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "merge_input_id": self.merge_input_id,
            "scorecards": [scorecard.as_dict() for scorecard in self.scorecards],
            "decision": self.decision.as_dict(),
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
            "evidence_gaps": list(self.evidence_gaps),
            "generated_for_review_only": self.generated_for_review_only,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SpecialistMergePlan:
    plan_id: str
    merge_input_ids: tuple[str, ...]
    decision_ids: tuple[str, ...] = ()
    provider_calls_enabled: bool = False
    active_specialist_routing_enabled: bool = False
    authority_transfer_enabled: bool = False
    canonical_write_enabled: bool = False
    memory_mutation_enabled: bool = False
    runtime_recall_mutation_enabled: bool = False
    training_enabled: bool = False
    execution_enabled: bool = False
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14J_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "merge_input_ids": list(self.merge_input_ids),
            "decision_ids": list(self.decision_ids),
            "provider_calls_enabled": self.provider_calls_enabled,
            "active_specialist_routing_enabled": self.active_specialist_routing_enabled,
            "authority_transfer_enabled": self.authority_transfer_enabled,
            "canonical_write_enabled": self.canonical_write_enabled,
            "memory_mutation_enabled": self.memory_mutation_enabled,
            "runtime_recall_mutation_enabled": self.runtime_recall_mutation_enabled,
            "training_enabled": self.training_enabled,
            "execution_enabled": self.execution_enabled,
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_specialist_evidence_packet(
    *,
    specialist_name: str,
    packet_source: SpecialistPacketSource = SpecialistPacketSource.MOCK_RESULT,
    source_reference_ids: tuple[str, ...] | list[str] = (),
    lane_scope: tuple[str, ...] | list[str] = (),
    summary: str = "",
    notes: str = "",
) -> SpecialistEvidencePacket:
    packet_id = _stable_id("specialist-packet", specialist_name, packet_source.value, source_reference_ids, lane_scope, summary)
    return SpecialistEvidencePacket(
        packet_id=packet_id,
        specialist_name=specialist_name,
        packet_source=packet_source,
        source_reference_ids=tuple(source_reference_ids),
        lane_scope=tuple(lane_scope),
        summary=summary,
        notes=notes,
    )


def create_specialist_result_claim(
    *,
    packet_id: str,
    claim_text: str,
    claim_type: SpecialistClaimType = SpecialistClaimType.EVIDENCE_OBSERVATION,
    confidence_state: float = 0.0,
    lane_scope: tuple[str, ...] | list[str] = (),
    provenance_reference_ids: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> SpecialistResultClaim:
    claim_id = _stable_id("specialist-claim", packet_id, claim_text, claim_type.value, lane_scope, provenance_reference_ids)
    return SpecialistResultClaim(
        claim_id=claim_id,
        packet_id=packet_id,
        claim_text=claim_text,
        claim_type=claim_type,
        confidence_state=confidence_state,
        lane_scope=tuple(lane_scope),
        provenance_reference_ids=tuple(provenance_reference_ids),
        notes=notes,
    )


def create_specialist_evidence_link(
    *,
    claim_id: str,
    target_reference_id: str,
    evidence_relation: SpecialistEvidenceRelation,
    evidence_weight: float = 0.0,
    rationale: str = "",
    provenance_reference_ids: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> SpecialistEvidenceLink:
    link_id = _stable_id("specialist-link", claim_id, target_reference_id, evidence_relation.value, evidence_weight, rationale)
    return SpecialistEvidenceLink(
        link_id=link_id,
        claim_id=claim_id,
        target_reference_id=target_reference_id,
        evidence_relation=evidence_relation,
        evidence_weight=evidence_weight,
        rationale=rationale,
        provenance_reference_ids=tuple(provenance_reference_ids),
        notes=notes,
    )


def create_specialist_merge_input(
    *,
    packets: tuple[SpecialistEvidencePacket, ...] | list[SpecialistEvidencePacket],
    claims: tuple[SpecialistResultClaim, ...] | list[SpecialistResultClaim] = (),
    evidence_links: tuple[SpecialistEvidenceLink, ...] | list[SpecialistEvidenceLink] = (),
    source_artifact_references: tuple[str, ...] | list[str] = (),
    lane_scope: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> SpecialistMergeInput:
    packet_ids = tuple(packet.packet_id for packet in packets)
    claim_ids = tuple(claim.claim_id for claim in claims)
    link_ids = tuple(link.link_id for link in evidence_links)
    merge_input_id = _stable_id("specialist-merge-input", packet_ids, claim_ids, link_ids, source_artifact_references, lane_scope)
    return SpecialistMergeInput(
        merge_input_id=merge_input_id,
        packets=tuple(packets),
        claims=tuple(claims),
        evidence_links=tuple(evidence_links),
        source_artifact_references=tuple(source_artifact_references),
        lane_scope=tuple(lane_scope),
        notes=notes,
    )


def create_specialist_merge_conflict(
    *,
    packet_ids: tuple[str, ...] | list[str],
    claim_ids: tuple[str, ...] | list[str],
    conflict_type: SpecialistMergeConflictType,
    rationale: str = "",
    source_reference_ids: tuple[str, ...] | list[str] = (),
    requires_human_review: bool = False,
    requires_replay_review: bool = False,
    notes: str = "",
) -> SpecialistMergeConflict:
    ordered_packet_ids = tuple(sorted(packet_ids))
    ordered_claim_ids = tuple(sorted(claim_ids))
    conflict_id = _stable_id("specialist-merge-conflict", ordered_packet_ids, ordered_claim_ids, conflict_type.value, rationale)
    return SpecialistMergeConflict(
        conflict_id=conflict_id,
        packet_ids=ordered_packet_ids,
        claim_ids=ordered_claim_ids,
        conflict_type=conflict_type,
        rationale=rationale,
        source_reference_ids=tuple(source_reference_ids),
        requires_human_review=requires_human_review,
        requires_replay_review=requires_replay_review,
        notes=notes,
    )


def score_specialist_merge_input(merge_input: SpecialistMergeInput) -> tuple[SpecialistMergeScorecard, ...]:
    return tuple(_score_claim(claim, merge_input.evidence_links, merge_input.conflicts if hasattr(merge_input, "conflicts") else ()) for claim in merge_input.claims)


def decide_specialist_merge(
    merge_input: SpecialistMergeInput,
    scorecards: tuple[SpecialistMergeScorecard, ...] | list[SpecialistMergeScorecard],
    conflicts: tuple[SpecialistMergeConflict, ...] | list[SpecialistMergeConflict] = (),
    *,
    force_blocked: bool = False,
) -> SpecialistMergeDecision:
    scorecards = tuple(scorecards)
    conflicts = tuple(conflicts)
    decision_basis = (
        merge_input.merge_input_id,
        tuple(scorecard.scorecard_id for scorecard in scorecards),
        tuple(conflict.conflict_id for conflict in conflicts),
        force_blocked,
    )
    decision_id = _stable_id("specialist-merge-decision", *decision_basis)
    if force_blocked or any(value is True for value in RUNTIME_V14J_INVARIANT_FLAGS.values()):
        outcome = SpecialistMergeOutcome.BLOCKED_BY_INVARIANT
        rationale = "Merge blocked by invariant; no provider call, authority transfer, or mutation is permitted."
        candidates: tuple[str, ...] = ()
    elif any(conflict.requires_human_review for conflict in conflicts):
        outcome = SpecialistMergeOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Specialist evidence conflict requires human review; no authority transfer occurs."
        candidates = ()
    elif any(conflict.requires_replay_review for conflict in conflicts):
        outcome = SpecialistMergeOutcome.REQUIRES_REPLAY_REVIEW
        rationale = "Specialist evidence conflict requires replay review; merge remains report-only."
        candidates = ()
    elif not scorecards:
        outcome = SpecialistMergeOutcome.DEFER_MERGE
        rationale = "No specialist claims are available to compare."
        candidates = ()
    else:
        candidates = tuple(
            scorecard.claim_id
            for scorecard in sorted(scorecards, key=lambda item: item.merge_readiness_score, reverse=True)
            if scorecard.merge_readiness_score >= 0.45
        )
        if candidates:
            outcome = SpecialistMergeOutcome.REPORT_ONLY_MERGE_CANDIDATE
            rationale = "Specialist evidence is a report-only merge candidate, not truth or authority."
        else:
            outcome = SpecialistMergeOutcome.DEFER_MERGE
            rationale = "Specialist evidence remains below merge-readiness threshold."
    rejected = tuple(scorecard.claim_id for scorecard in scorecards if scorecard.merge_readiness_score < 0.2)
    return SpecialistMergeDecision(
        decision_id=decision_id,
        merge_input_id=merge_input.merge_input_id,
        outcome=outcome,
        merge_candidate_claim_ids=candidates,
        rejected_claim_ids=rejected,
        rationale=rationale,
    )


def create_specialist_merge_report(
    merge_input: SpecialistMergeInput,
    scorecards: tuple[SpecialistMergeScorecard, ...] | list[SpecialistMergeScorecard],
    decision: SpecialistMergeDecision,
    conflicts: tuple[SpecialistMergeConflict, ...] | list[SpecialistMergeConflict] = (),
    evidence_gaps: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> SpecialistMergeReport:
    report_id = _stable_id(
        "specialist-merge-report",
        merge_input.merge_input_id,
        tuple(scorecard.scorecard_id for scorecard in scorecards),
        decision.decision_id,
    )
    return SpecialistMergeReport(
        report_id=report_id,
        merge_input_id=merge_input.merge_input_id,
        scorecards=tuple(scorecards),
        decision=decision,
        conflicts=tuple(conflicts),
        evidence_gaps=tuple(evidence_gaps),
        notes=notes,
    )


def create_specialist_merge_plan(
    *,
    merge_inputs: tuple[SpecialistMergeInput, ...] | list[SpecialistMergeInput] = (),
    decisions: tuple[SpecialistMergeDecision, ...] | list[SpecialistMergeDecision] = (),
    notes: str = "",
) -> SpecialistMergePlan:
    input_ids = tuple(item.merge_input_id for item in merge_inputs)
    decision_ids = tuple(item.decision_id for item in decisions)
    plan_id = _stable_id("specialist-merge-plan", input_ids, decision_ids, notes)
    return SpecialistMergePlan(
        plan_id=plan_id,
        merge_input_ids=input_ids,
        decision_ids=decision_ids,
        notes=notes,
    )


def validate_specialist_packet_inert(packet: SpecialistEvidencePacket) -> bool:
    return (
        packet.provider_call_performed is False
        and packet.active_routing_used is False
        and packet.authority_granted is False
        and packet.canonical is False
    )


def validate_specialist_claim_inert(claim: SpecialistResultClaim) -> bool:
    return claim.accepted_as_truth is False and claim.learned is False and claim.canonical is False


def validate_specialist_merge_input_inert(merge_input: SpecialistMergeInput) -> bool:
    return (
        merge_input.provider_calls_enabled is False
        and merge_input.active_specialist_routing_enabled is False
        and merge_input.authority_transfer_enabled is False
        and all(validate_specialist_packet_inert(packet) for packet in merge_input.packets)
        and all(validate_specialist_claim_inert(claim) for claim in merge_input.claims)
    )


def validate_specialist_scorecard_report_only(scorecard: SpecialistMergeScorecard) -> bool:
    return scorecard.authoritative is False


def validate_specialist_merge_decision_report_only(decision: SpecialistMergeDecision) -> bool:
    return (
        decision.applied is False
        and decision.authoritative is False
        and decision.provider_called is False
        and all(value is False for value in decision.invariant_flags.values())
    )


def validate_specialist_merge_report_review_only(report: SpecialistMergeReport) -> bool:
    return (
        report.generated_for_review_only is True
        and validate_specialist_merge_decision_report_only(report.decision)
        and all(validate_specialist_scorecard_report_only(scorecard) for scorecard in report.scorecards)
    )


def validate_specialist_merge_plan_inert(plan: SpecialistMergePlan) -> bool:
    return (
        plan.provider_calls_enabled is False
        and plan.active_specialist_routing_enabled is False
        and plan.authority_transfer_enabled is False
        and plan.canonical_write_enabled is False
        and plan.memory_mutation_enabled is False
        and plan.runtime_recall_mutation_enabled is False
        and plan.training_enabled is False
        and plan.execution_enabled is False
        and all(value is False for value in plan.invariant_flags.values())
    )


def _score_claim(
    claim: SpecialistResultClaim,
    links: tuple[SpecialistEvidenceLink, ...],
    conflicts: tuple[SpecialistMergeConflict, ...] = (),
) -> SpecialistMergeScorecard:
    claim_links = tuple(link for link in links if link.claim_id == claim.claim_id)
    support_score = _support_score(claim_links)
    contradiction_score = _contradiction_score(claim_links, claim, conflicts)
    provenance_score = _provenance_score(claim)
    safety_score = 0.0 if any(link.evidence_relation == SpecialistEvidenceRelation.UNSAFE_TO_MERGE for link in claim_links) else 1.0
    readiness = _clamp((support_score * 0.42) + (provenance_score * 0.24) + (safety_score * 0.24) - (contradiction_score * 0.3))
    scorecard_id = _stable_id("specialist-merge-scorecard", claim.claim_id, support_score, contradiction_score, provenance_score, safety_score)
    return SpecialistMergeScorecard(
        scorecard_id=scorecard_id,
        claim_id=claim.claim_id,
        support_score=support_score,
        contradiction_score=contradiction_score,
        provenance_score=provenance_score,
        safety_score=safety_score,
        merge_readiness_score=readiness,
        rationale="report-only specialist evidence score; not authority",
    )


def _support_score(links: tuple[SpecialistEvidenceLink, ...]) -> float:
    if not links:
        return 0.0
    supporting = [
        link.normalized_weight()
        for link in links
        if link.evidence_relation
        in {
            SpecialistEvidenceRelation.SUPPORTS,
            SpecialistEvidenceRelation.WEAKLY_SUPPORTS,
            SpecialistEvidenceRelation.CLARIFIES,
        }
    ]
    if not supporting:
        return 0.0
    return _clamp(sum(supporting) / len(supporting))


def _contradiction_score(
    links: tuple[SpecialistEvidenceLink, ...],
    claim: SpecialistResultClaim,
    conflicts: tuple[SpecialistMergeConflict, ...],
) -> float:
    contradictory = [
        link.normalized_weight()
        for link in links
        if link.evidence_relation
        in {
            SpecialistEvidenceRelation.CONTRADICTS,
            SpecialistEvidenceRelation.WEAKLY_CONTRADICTS,
            SpecialistEvidenceRelation.UNSAFE_TO_MERGE,
        }
    ]
    conflict_pressure = 0.35 if any(claim.claim_id in conflict.claim_ids for conflict in conflicts) else 0.0
    if not contradictory:
        return conflict_pressure
    return _clamp((sum(contradictory) / len(contradictory)) + conflict_pressure)


def _provenance_score(claim: SpecialistResultClaim) -> float:
    if not claim.provenance_reference_ids:
        return 0.0
    return _clamp(min(1.0, len(set(claim.provenance_reference_ids)) / 3.0))


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
