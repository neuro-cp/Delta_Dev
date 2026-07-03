from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_replay import RUNTIME_V14E_INVARIANT_FLAGS, ReplayBatch, ReplayReviewResult


class ConsolidationCandidateKind(str, Enum):
    EPISODE_SUMMARY = "episode_summary"
    FEEDBACK_PATTERN = "feedback_pattern"
    PRUNING_REVIEW = "pruning_review"
    SEMANTIC_CANDIDATE = "semantic_candidate"
    UNKNOWN = "unknown"


class ConsolidationDecisionOutcome(str, Enum):
    DEFER = "defer"
    REJECT = "reject"
    CANDIDATE_ONLY = "candidate_only"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"


@dataclass(frozen=True)
class ConsolidationCandidate:
    candidate_id: str
    source_batch_id: str
    source_review_id: str
    candidate_kind: ConsolidationCandidateKind
    source_episode_ids: tuple[str, ...] = ()
    source_feedback_ids: tuple[str, ...] = ()
    source_replay_marker_ids: tuple[str, ...] = ()
    source_pruning_proposal_ids: tuple[str, ...] = ()
    summary: str = ""
    rationale: str = ""
    confidence: float = 0.0
    candidate_only: bool = True
    canonical_memory: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "source_batch_id": self.source_batch_id,
            "source_review_id": self.source_review_id,
            "candidate_kind": self.candidate_kind.value,
            "source_episode_ids": list(self.source_episode_ids),
            "source_feedback_ids": list(self.source_feedback_ids),
            "source_replay_marker_ids": list(self.source_replay_marker_ids),
            "source_pruning_proposal_ids": list(self.source_pruning_proposal_ids),
            "summary": self.summary,
            "rationale": self.rationale,
            "confidence": self.normalized_confidence(),
            "candidate_only": self.candidate_only,
            "canonical_memory": self.canonical_memory,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ConsolidationDecision:
    decision_id: str
    candidate_id: str
    outcome: ConsolidationDecisionOutcome
    rationale: str
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14E_INVARIANT_FLAGS))
    applied: bool = False
    canonical_write_enabled: bool = False
    training_enabled: bool = False
    pruning_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "outcome": self.outcome.value,
            "rationale": self.rationale,
            "invariant_flags": dict(self.invariant_flags),
            "applied": self.applied,
            "canonical_write_enabled": self.canonical_write_enabled,
            "training_enabled": self.training_enabled,
            "pruning_enabled": self.pruning_enabled,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def create_consolidation_candidate(
    review_result: ReplayReviewResult,
    batch: ReplayBatch,
    *,
    candidate_kind: ConsolidationCandidateKind = ConsolidationCandidateKind.UNKNOWN,
    summary: str = "",
    rationale: str = "",
) -> ConsolidationCandidate:
    confidence = _candidate_confidence(review_result)
    return ConsolidationCandidate(
        candidate_id=_stable_id(
            "consolidation-candidate",
            (
                batch.batch_id,
                review_result.review_id,
                candidate_kind.value,
                *batch.episode_ids,
                *batch.feedback_ids,
                *batch.replay_marker_ids,
                *batch.pruning_proposal_ids,
            ),
        ),
        source_batch_id=batch.batch_id,
        source_review_id=review_result.review_id,
        candidate_kind=candidate_kind,
        source_episode_ids=batch.episode_ids,
        source_feedback_ids=batch.feedback_ids,
        source_replay_marker_ids=batch.replay_marker_ids,
        source_pruning_proposal_ids=batch.pruning_proposal_ids,
        summary=summary or "Replay review produced a candidate for later consolidation review.",
        rationale=rationale or review_result.rationale,
        confidence=confidence,
        notes="candidate is inert; it is not canonical memory and is not applied",
    )


def decide_consolidation_candidate(
    candidate: ConsolidationCandidate,
    *,
    require_human_review: bool = False,
    invariant_block: bool = False,
    reject: bool = False,
    defer: bool = False,
) -> ConsolidationDecision:
    if invariant_block:
        outcome = ConsolidationDecisionOutcome.BLOCKED_BY_INVARIANT
        rationale = "A V1.4E invariant blocked consolidation."
    elif require_human_review:
        outcome = ConsolidationDecisionOutcome.REQUIRES_HUMAN_REVIEW
        rationale = "Candidate requires human review before any future consolidation."
    elif reject:
        outcome = ConsolidationDecisionOutcome.REJECT
        rationale = "Candidate is rejected at review time; no memory mutation is performed."
    elif defer or candidate.normalized_confidence() < 0.4:
        outcome = ConsolidationDecisionOutcome.DEFER
        rationale = "Candidate needs more evidence before future consolidation."
    else:
        outcome = ConsolidationDecisionOutcome.CANDIDATE_ONLY
        rationale = "Candidate may be carried forward for future review only."
    return ConsolidationDecision(
        decision_id=_stable_id("consolidation-decision", (candidate.candidate_id, outcome.value)),
        candidate_id=candidate.candidate_id,
        outcome=outcome,
        rationale=rationale,
        notes="decision is review-only; applied remains false",
    )


def validate_consolidation_candidate_non_mutating(candidate: ConsolidationCandidate) -> bool:
    return candidate.candidate_only and not candidate.canonical_memory


def validate_consolidation_decision_review_only(decision: ConsolidationDecision) -> bool:
    return (
        decision.applied is False
        and decision.canonical_write_enabled is False
        and decision.training_enabled is False
        and decision.pruning_enabled is False
        and all(value is False for value in decision.invariant_flags.values())
    )


def _candidate_confidence(review_result: ReplayReviewResult) -> float:
    signal = review_result.useful_signal_count
    penalties = (
        review_result.insufficient_evidence_count
        + review_result.conflicting_evidence_count
        + review_result.safety_blocked_count
    )
    if review_result.human_review_needed:
        penalties += 1
    return max(0.0, min(1.0, 0.45 + (0.15 * signal) - (0.12 * penalties)))


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"
