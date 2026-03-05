from __future__ import annotations

from typing import List, Iterable

from memory.attention.attention_item import AttentionItem
from memory.attention.attention_policy import AttentionPolicy


class AttentionField:
    """
    Active attention field.

    CONTRACT:
    - Holds transient AttentionItems
    - Applies decay and suppression
    - Normalizes gains
    - Accepts read-only ingestion
    - No interpretation
    """

    def __init__(
        self,
        *,
        policy: AttentionPolicy,
    ) -> None:
        self._policy = policy
        self._items: List[AttentionItem] = []

    def items(self) -> List[AttentionItem]:
        return list(self._items)

    def add(self, item: AttentionItem) -> None:
        self._items.append(item)

    def ingest(self, items: Iterable[AttentionItem]) -> None:
        """
        Ingest attention proposals.

        CONTRACT:
        - Append-only
        - No decay
        - No suppression
        - No normalization
        """
        for item in items:
            self._items.append(item)

    def step(self, *, current_step: int) -> None:
        # --------------------------------------------------
        # 1. decay
        # --------------------------------------------------
        decayed = [
            self._policy.decay(item, current_step=current_step)
            for item in self._items
        ]

        # --------------------------------------------------
        # 2. suppress
        # --------------------------------------------------
        kept = [
            item for item in decayed
            if not self._policy.should_suppress(item)
        ]

        # --------------------------------------------------
        # 3. normalize
        # --------------------------------------------------
        self._items = self._policy.normalize(kept)
