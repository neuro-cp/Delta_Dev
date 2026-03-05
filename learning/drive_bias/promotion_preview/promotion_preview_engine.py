
from __future__ import annotations
from typing import Iterable, List, Dict

from learning.schemas.learning_proposal import LearningProposal
from learning.drive_bias.promotion_preview.promotion_preview_policy import (
    PromotionPreviewPolicy,
)


class PromotionPreviewEngine:
    '''
    Offline promotion preview.

    CONTRACT:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    - Preview only
    '''

    def __init__(self) -> None:
        self._policy = PromotionPreviewPolicy()

    def preview(
        self,
        *,
        proposals: Iterable[LearningProposal],
        selected_ids: Iterable[str],
        scores: Dict[str, float],
        threshold: float = 0.0,
    ) -> List[str]:

        proposal_ids = {p.proposal_id for p in proposals}
        valid_selected = [pid for pid in selected_ids if pid in proposal_ids]

        return self._policy.select_promotable(
            selected_ids=valid_selected,
            scores=scores,
            threshold=threshold,
        )
