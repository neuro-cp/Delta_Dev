from __future__ import annotations

from typing import Dict

from memory.drive.drive_field import DriveField


class DriveToWorkingMemoryAdapter:
    """
    Computes working-memory bias suggestions from drive.

    CONTRACT:
    - Read-only
    - No mutation of WM
    """

    def __init__(self, *, field: DriveField) -> None:
        self._field = field

    def compute_decay_bias(self) -> Dict[str, float]:
        """
        Returns decay-rate multipliers keyed by drive.
        """
        biases: Dict[str, float] = {}

        for s in self._field.signals():
            biases[s.key] = max(0.0, 1.0 - s.magnitude)

        return biases
