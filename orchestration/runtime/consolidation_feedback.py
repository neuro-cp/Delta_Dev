"""Read-only cognitive consequences derived from canonical consolidation state."""

from __future__ import annotations

from dataclasses import dataclass

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.provisional_semantic_consolidation import ProvisionalSemanticGraphState


@dataclass(frozen=True)
class ConsolidationFeedback:
    """A review consequence, never a second durable owner."""

    feedback_id: str
    review_id: str
    claim_version_id: str
    verdict: str
    admission_action: str
    cognitive_consequence: str
    factual_use: str
    rationale: str
    source_ids: tuple[str, ...]


def derive_consolidation_feedback(graph: ProvisionalSemanticGraphState) -> tuple[ConsolidationFeedback, ...]:
    """Project immutable reviews and admissions into bounded cognitive consequences."""

    admissions = {(item.review_id, item.claim_version_id): item for item in graph.admissions}
    feedback: list[ConsolidationFeedback] = []
    for review in graph.reviews:
        for item in review.claim_reviews:
            version_id = str(item.get("claim_version_id") or "")
            verdict = str(item.get("verdict") or "")
            if not version_id or not verdict:
                continue
            admission = admissions.get((review.review_id, version_id))
            action = admission.action if admission is not None else "pending_operator_consolidation_review"
            consequence, factual_use = _consequence(verdict, action)
            source_ids = (review.review_id, review.packet_id, version_id)
            feedback.append(ConsolidationFeedback(
                feedback_id=stable_id("consolidation-feedback", *source_ids, verdict, action),
                review_id=review.review_id,
                claim_version_id=version_id,
                verdict=verdict,
                admission_action=action,
                cognitive_consequence=consequence,
                factual_use=factual_use,
                rationale=str(item.get("rationale_code") or verdict),
                source_ids=source_ids,
            ))
    return tuple(sorted(feedback, key=lambda item: item.feedback_id))


def _consequence(verdict: str, action: str) -> tuple[str, str]:
    if action == "pending_operator_consolidation_review":
        return "visible_pending_review", "not_reviewed"
    if verdict == "validated":
        return "reviewed_support_available", "eligible_after_admission"
    if verdict == "partially_valid":
        return "targeted_remaining_gap", "partial_only"
    if verdict == "requires_revision":
        return "revisit_required", "provisional_only"
    if verdict == "unsupported":
        return "suppress_factual_use_retain_trace", "suppressed"
    if verdict in {"contradicted", "invalid"}:
        return "high_priority_contradiction_review", "withheld"
    return "quarantined_pending_review", "withheld"


__all__ = ["ConsolidationFeedback", "derive_consolidation_feedback"]
