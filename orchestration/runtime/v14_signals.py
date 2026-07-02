from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class EvidenceFunction(str, Enum):
    CAUSAL_EVIDENCE = "causal_evidence"
    CONTRADICTION_EVIDENCE = "contradiction_evidence"
    EXCEPTION_EVIDENCE = "exception_evidence"
    CONSTRAINT_EVIDENCE = "constraint_evidence"
    REVISION_EVIDENCE = "revision_evidence"
    TRADEOFF_EVIDENCE = "tradeoff_evidence"
    UNCERTAINTY_EVIDENCE = "uncertainty_evidence"
    PLANNING_DEPENDENCY = "planning_dependency"
    GENERIC_CONTEXT = "generic_context"
    UNKNOWN = "unknown"


class CausalRole(str, Enum):
    CAUSE = "cause"
    EFFECT = "effect"
    MEDIATOR = "mediator"
    INHIBITOR = "inhibitor"
    AMPLIFIER = "amplifier"
    PRECONDITION = "precondition"
    CONSEQUENCE = "consequence"
    UNKNOWN = "unknown"


class ClaimPolarity(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    UNCERTAIN = "uncertain"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ContradictionDirection(str, Enum):
    DIRECT_CONFLICT = "direct_conflict"
    EXCEPTION_TO_RULE = "exception_to_rule"
    WEAKENS_CLAIM = "weakens_claim"
    REVERSES_CLAIM = "reverses_claim"
    NO_CONTRADICTION = "no_contradiction"
    UNKNOWN = "unknown"


class DecisionCriticality(str, Enum):
    ACTION_BLOCKING = "action_blocking"
    ACTION_GUIDING = "action_guiding"
    CONTEXT_ONLY = "context_only"
    LOW = "low"
    UNKNOWN = "unknown"


class UncertaintyRole(str, Enum):
    RISK_MARKER = "risk_marker"
    MISSING_EVIDENCE = "missing_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    ESTIMATE = "estimate"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EvidenceRoleMetadata:
    evidence_function: EvidenceFunction = EvidenceFunction.UNKNOWN
    causal_role: CausalRole = CausalRole.UNKNOWN
    claim_polarity: ClaimPolarity = ClaimPolarity.UNKNOWN
    contradiction_direction: ContradictionDirection = ContradictionDirection.UNKNOWN
    decision_criticality: DecisionCriticality = DecisionCriticality.UNKNOWN
    uncertainty_role: UncertaintyRole = UncertaintyRole.UNKNOWN
    confidence: float = 0.0
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_function": self.evidence_function.value,
            "causal_role": self.causal_role.value,
            "claim_polarity": self.claim_polarity.value,
            "contradiction_direction": self.contradiction_direction.value,
            "decision_criticality": self.decision_criticality.value,
            "uncertainty_role": self.uncertainty_role.value,
            "confidence": self.normalized_confidence(),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SemanticSignalSet:
    evidence_role: EvidenceRoleMetadata = field(default_factory=EvidenceRoleMetadata)
    relation_terms: tuple[str, ...] = ()
    action_terms: tuple[str, ...] = ()
    outcome_terms: tuple[str, ...] = ()
    constraint_terms: tuple[str, ...] = ()
    uncertainty_terms: tuple[str, ...] = ()
    source: str = "unknown"

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_role": self.evidence_role.as_dict(),
            "relation_terms": list(self.relation_terms),
            "action_terms": list(self.action_terms),
            "outcome_terms": list(self.outcome_terms),
            "constraint_terms": list(self.constraint_terms),
            "uncertainty_terms": list(self.uncertainty_terms),
            "source": self.source,
        }


def empty_signal_set(source: str = "empty") -> SemanticSignalSet:
    return SemanticSignalSet(source=source)


def merge_signal_sets(*signal_sets: SemanticSignalSet, source: str = "merged") -> SemanticSignalSet:
    if not signal_sets:
        return empty_signal_set(source=source)
    best_role = max(
        (signal.evidence_role for signal in signal_sets),
        key=lambda role: role.normalized_confidence(),
    )
    return SemanticSignalSet(
        evidence_role=best_role,
        relation_terms=_merge_terms(signal.relation_terms for signal in signal_sets),
        action_terms=_merge_terms(signal.action_terms for signal in signal_sets),
        outcome_terms=_merge_terms(signal.outcome_terms for signal in signal_sets),
        constraint_terms=_merge_terms(signal.constraint_terms for signal in signal_sets),
        uncertainty_terms=_merge_terms(signal.uncertainty_terms for signal in signal_sets),
        source=source,
    )


def is_strong_evidence_role(role: EvidenceRoleMetadata) -> bool:
    if role.normalized_confidence() < 0.65:
        return False
    if role.evidence_function in {EvidenceFunction.UNKNOWN, EvidenceFunction.GENERIC_CONTEXT}:
        return False
    return (
        role.decision_criticality
        in {DecisionCriticality.ACTION_BLOCKING, DecisionCriticality.ACTION_GUIDING}
        or role.claim_polarity in {ClaimPolarity.SUPPORTS, ClaimPolarity.CONTRADICTS, ClaimPolarity.QUALIFIES}
        or role.uncertainty_role
        in {UncertaintyRole.RISK_MARKER, UncertaintyRole.MISSING_EVIDENCE, UncertaintyRole.CONFLICTING_EVIDENCE}
    )


def _merge_terms(term_groups: Iterable[Iterable[str]]) -> tuple[str, ...]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in term_groups:
        for raw in group:
            term = str(raw).strip().lower()
            if term and term not in seen:
                seen.add(term)
                merged.append(term)
    return tuple(merged)
