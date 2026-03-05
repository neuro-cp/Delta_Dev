
from __future__ import annotations
from typing import Iterable, List


class PromotionPreviewPolicy:
    '''
    Pure selection rule for previewing promotable proposals.

    CONTRACT:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    '''

    def select_promotable(
        self,
        *,
        selected_ids: Iterable[str],
        scores: dict[str, float],
        threshold: float,
    ) -> List[str]:

        promotable: List[str] = []

        for pid in selected_ids:
            score = scores.get(pid, 0.0)
            if score >= threshold:
                promotable.append(pid)

        return sorted(promotable)
