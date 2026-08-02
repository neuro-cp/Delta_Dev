"""Claim-bound answer posture selection; ordinary chat remains unmodified."""

from __future__ import annotations

from orchestration.runtime.provisional_semantic_consolidation import ProvisionalSemanticGraphState


def resolve_epistemic_answer_mode(graph: ProvisionalSemanticGraphState, claim_version_ids: tuple[str, ...]) -> str:
    """Return a conservative presentation mode from canonical claim state."""

    if not claim_version_ids:
        return "ordinary_conversation"
    states = {
        item.epistemic_state
        for item in graph.claim_versions
        if item.claim_version_id in set(claim_version_ids)
    }
    if not states:
        return "insufficient_verified_knowledge"
    if states & {"contradicted", "locally_contradicted", "invalidated", "quarantined"}:
        return "contradicted_or_unstable"
    if states & {"pending_operator_consolidation_review", "escalated_operator"}:
        return "operator_review_required"
    if states & {"pending_consolidation", "provisional"}:
        return "consolidation_in_progress"
    if states == {"validated"}:
        return "validated_answer"
    if states <= {"validated", "partially_valid"}:
        return "validated_partial_answer"
    if states & {"uncertain", "insufficient_local_evidence", "requires_revision", "unsupported"}:
        return "provisional_answer"
    return "insufficient_verified_knowledge"


__all__ = ["resolve_epistemic_answer_mode"]
