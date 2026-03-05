from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from memory.semantic_promotion.promotion_candidate import PromotionCandidate


@dataclass(frozen=True)
class PromotionDiff:
    """
    Descriptive diff between two promotion runs.

    Semantic-ID–centric.
    Read-only.
    No authority.
    """

    became_eligible: List[str]
    became_ineligible: List[str]
    reason_deltas: Dict[str, int]


class PromotionDiffBuilder:
    """
    Computes descriptive differences between two promotion candidate sets.

    CONTRACT:
    - Read-only
    - Deterministic
    - semantic_id–based identity
    - No thresholds
    - No decisions
    """

    def build(
        self,
        *,
        before: List[PromotionCandidate],
        after: List[PromotionCandidate],
    ) -> PromotionDiff:
        before_map = {c.semantic_id: c for c in before}
        after_map = {c.semantic_id: c for c in after}

        became_eligible: List[str] = []
        became_ineligible: List[str] = []
        reason_deltas: Dict[str, int] = {}

        for sid, after_c in after_map.items():
            before_c = before_map.get(sid)
            if before_c is None:
                continue

            if before_c.disqualified and not after_c.disqualified:
                became_eligible.append(sid)

            if not before_c.disqualified and after_c.disqualified:
                became_ineligible.append(sid)

            for reason in after_c.disqualification_reasons:
                reason_deltas[reason] = reason_deltas.get(reason, 0) + 1

        return PromotionDiff(
            became_eligible=became_eligible,
            became_ineligible=became_ineligible,
            reason_deltas=reason_deltas,
        )
