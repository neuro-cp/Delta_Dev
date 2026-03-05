from __future__ import annotations

from typing import Dict, Any

from engine.vta_value.value_engine import ValueEngine


class ValueRuntimeHook:
    """
    Read-only runtime hook for value.

    CONTRACT:
    - No mutation
    - No bias application
    - Snapshot only
    """

    def __init__(self, *, engine: ValueEngine) -> None:
        self._engine = engine
        self._current_step: int = 0

    def step(self, *, current_step: int) -> None:
        self._current_step = current_step

    def snapshot(self) -> Dict[str, Any]:
        signal = self._engine.signal

        return {
            "current_step": self._current_step,
            "value": signal.value,
        }
