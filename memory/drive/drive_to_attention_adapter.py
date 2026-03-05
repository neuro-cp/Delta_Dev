from __future__ import annotations

from typing import Dict

from memory.drive.drive_field import DriveField


class DriveToAttentionAdapter:
    """
    Computes attention gain modifiers from drive state.

    CONTRACT:
    - Read-only
    - Bounded
    - No direct field mutation
    """

    def __init__(self, *, field: DriveField) -> None:
        self._field = field

    def compute_gain_bias(self) -> Dict[str, float]:
        """
        Returns multiplicative gain biases keyed by drive.
        """
        biases: Dict[str, float] = {}

        for s in self._field.signals():
            biases[s.key] = 1.0 + s.magnitude

        return biases
