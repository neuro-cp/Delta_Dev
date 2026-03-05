# memory/semantic_promotion/promotion_execution_adapter.py

from __future__ import annotations

from typing import Iterable, List, Optional

from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.semantic_promotion.promoted_semantic import PromotedSemantic


class PromotionExecutionAdapter:
    """
    Offline adapter that materializes promoted semantics
    from promotion candidates.

    CONTRACT:
    - Offline only
    - Read-only inputs
    - Deterministic
    - No runtime authority
    - No mutation
    - No learning semantics
    - Explicit policy-version carrythrough

    This adapter performs *execution* in the narrow sense:
    eligibility → existence, nothing more.
    """

    def execute(
        self,
        *,
        candidates: Iterable[PromotionCandidate],
        promotion_step: Optional[int],
        promotion_time: Optional[float],
    ) -> List[PromotedSemantic]:
        promoted: List[PromotedSemantic] = []

        for candidate in candidates:
            # Only eligible candidates may be executed
            if candidate.disqualified:
                continue

            promoted.append(
                PromotedSemantic(
                    semantic_id=candidate.semantic_id,
                    promotion_policy_version=candidate.policy_version,
                    promotion_step=promotion_step,
                    promotion_time=promotion_time,
                    source_candidate_ids=[candidate.semantic_id],
                    supporting_episode_ids=candidate.supporting_episode_ids,
                    recurrence_count=candidate.recurrence_count,
                    persistence_span=candidate.persistence_span,
                    stability_classification=candidate.stability_classification,
                    confidence_estimate=candidate.confidence_estimate,
                    tags=dict(candidate.tags) if candidate.tags else None,
                    notes=candidate.notes,
                )
            )

        return promoted
