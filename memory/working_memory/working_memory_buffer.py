from __future__ import annotations

from typing import List

from memory.working_memory.working_item import WorkingItem
from memory.working_memory.working_memory_policy import WorkingMemoryPolicy


class WorkingMemoryBuffer:
    """
    Bounded working-memory container.

    CONTRACT:
    - Holds transient WorkingItems
    - Enforces capacity
    - Applies decay BEFORE eviction
    - No interpretation
    """

    def __init__(
        self,
        *,
        capacity: int,
        policy: WorkingMemoryPolicy,
    ) -> None:
        self._capacity = capacity
        self._policy = policy
        self._items: List[WorkingItem] = []

    def items(self) -> List[WorkingItem]:
        return list(self._items)

    def insert(self, item: WorkingItem) -> None:
        self._items.append(item)
        self._evict_if_needed()

    def step(self, *, current_step: int) -> None:
        # --------------------------------------------------
        # 1. Apply decay to all items (forensic, monotonic)
        # --------------------------------------------------
        decayed: List[WorkingItem] = [
            self._policy.decay(item, current_step=current_step)
            for item in self._items
        ]

        # --------------------------------------------------
        # 2. Evict items that fall below threshold
        # --------------------------------------------------
        self._items = [
            item
            for item in decayed
            if not self._policy.should_evict(item, current_step=current_step)
        ]

        # --------------------------------------------------
        # 3. Enforce capacity (strength-based)
        # --------------------------------------------------
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        if len(self._items) <= self._capacity:
            return

        self._items = self._policy.select_evictions(
            items=self._items,
            max_items=self._capacity,
        )
