from __future__ import annotations

from typing import List

from memory.attention.attention_item import AttentionItem


class AttentionPolicy:
    """
    Policy governing attention decay and competition.

    CONTRACT:
    - Deterministic
    - Bounded gains
    - No learning
    """

    def __init__(
        self,
        *,
        decay_rate: float,
        min_gain: float,
        max_gain: float,
    ) -> None:
        self._decay_rate = decay_rate
        self._min_gain = min_gain
        self._max_gain = max_gain

    def decay(
        self,
        item: AttentionItem,
        *,
        current_step: int,
    ) -> AttentionItem:
        age = current_step - item.created_step
        new_gain = item.gain * (self._decay_rate ** age)
        new_gain = max(self._min_gain, min(self._max_gain, new_gain))

        return AttentionItem(
            key=item.key,
            gain=new_gain,
            created_step=item.created_step,
            source=item.source,
        )

    def should_suppress(self, item: AttentionItem) -> bool:
        return item.gain <= self._min_gain

    def normalize(self, items: List[AttentionItem]) -> List[AttentionItem]:
        if not items:
            return []

        total = sum(i.gain for i in items)
        if total <= 0:
            return items

        return [
            AttentionItem(
                key=i.key,
                gain=i.gain / total,
                created_step=i.created_step,
                source=i.source,
            )
            for i in items
        ]
