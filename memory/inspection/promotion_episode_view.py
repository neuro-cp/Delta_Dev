from __future__ import annotations

from dataclasses import dataclass
from typing import List

from memory.semantic_promotion.promotion_candidate import PromotionCandidate


@dataclass(frozen=True)
class PromotionEpisodeView:
    """
    Episode-scoped, human-facing promotion eligibility view.

    Descriptive only.
    No authority.
    """

    episode_id: int
    candidates: List[PromotionCandidate]


class PromotionEpisodeViewBuilder:
    """
    Builds episode-level promotion inspection views.

    CONTRACT:
    - Presentation only
    - No inference
    - No filtering
    """

    def build(
        self,
        *,
        episode_id: int,
        candidates: List[PromotionCandidate],
    ) -> PromotionEpisodeView:
        return PromotionEpisodeView(
            episode_id=episode_id,
            candidates=list(candidates),
        )
