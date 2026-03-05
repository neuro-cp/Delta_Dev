from __future__ import annotations

from typing import List, Optional

from memory.working_memory.working_item import WorkingItem


class WorkingMemoryPolicy:
    """
    Decay and eviction rules for working memory.

    CONTRACT:
    - Deterministic
    - No learning
    - No reward awareness
    - External decay bias is optional and identity by default
    """

    def __init__(
        self,
        *,
        decay_rate: float,
        min_strength: float,
    ) -> None:
        self._decay_rate = decay_rate
        self._min_strength = min_strength
        self._decay_bias: float = 1.0  # identity

    # --------------------------------------------------
    # Bias control (read-only external suggestion)
    # --------------------------------------------------
    def set_decay_bias(self, *, bias: float) -> None:
        """
        Set external decay bias.

        CONTRACT:
        - Bias is multiplicative
        - Identity = 1.0
        - Must be non-negative
        """
        if bias < 0.0:
            raise ValueError("Decay bias must be non-negative.")
        self._decay_bias = bias

    def clear_decay_bias(self) -> None:
        """
        Reset decay bias to identity.
        """
        self._decay_bias = 1.0

    # --------------------------------------------------
    # Core policy
    # --------------------------------------------------
    def decay(
        self,
        item: WorkingItem,
        *,
        current_step: int,
    ) -> WorkingItem:
        age = current_step - item.created_step

        effective_decay = self._decay_rate * self._decay_bias
        new_strength = item.strength * (effective_decay ** age)

        return WorkingItem(
            key=item.key,
            payload=item.payload,
            strength=new_strength,
            created_step=item.created_step,
            source=item.source,
        )

    def should_evict(
        self,
        item: WorkingItem,
        *,
        current_step: int,
    ) -> bool:
        return item.strength < self._min_strength

    def select_evictions(
        self,
        *,
        items: List[WorkingItem],
        max_items: int,
    ) -> List[WorkingItem]:
        # Keep strongest items only
        items_sorted = sorted(
            items,
            key=lambda i: i.strength,
            reverse=True,
        )
        return items_sorted[:max_items]
