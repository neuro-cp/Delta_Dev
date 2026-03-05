from __future__ import annotations

from typing import Dict, Any, List

from memory.working_memory.working_memory_buffer import WorkingMemoryBuffer


class WorkingMemoryRuntimeHook:
    """
    Read-only runtime hook for working memory.

    CONTRACT:
    - No runtime mutation
    - No decision influence
    - Snapshot is observational only
    """

    def __init__(self, *, buffer: WorkingMemoryBuffer) -> None:
        self._buffer = buffer
        self._current_step: int = 0

    def step(self, *, current_step: int) -> None:
        """
        Advance timebase for snapshot consistency.

        CONTRACT:
        - No mutation of buffer
        - Time tracking only
        """
        self._current_step = current_step

    def snapshot(self) -> Dict[str, Any]:
        items = self._buffer.items()

        # Reach policy through buffer (read-only inspection)
        policy = self._buffer._policy  # intentional: inspection only

        return {
            "current_step": self._current_step,
            "count": len(items),
            "total_strength": sum(i.strength for i in items),
            "decay_bias": getattr(policy, "_decay_bias", 1.0),
            "items": [
                {
                    "key": i.key,
                    "strength": i.strength,
                    "created_step": i.created_step,
                    "source": i.source,
                }
                for i in items
            ],
        }
