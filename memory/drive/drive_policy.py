from __future__ import annotations

from typing import List

from memory.drive.drive_signal import DriveSignal


class DrivePolicy:
    """
    Governs drive dynamics.

    CONTRACT:
    - Deterministic
    - Bounded
    - No learning
    """

    def __init__(
        self,
        *,
        decay_rate: float,
        min_magnitude: float,
        max_magnitude: float,
    ) -> None:
        self._decay_rate = decay_rate
        self._min = min_magnitude
        self._max = max_magnitude

    def decay(
        self,
        signal: DriveSignal,
        *,
        current_step: int,
    ) -> DriveSignal:
        age = current_step - signal.created_step
        mag = signal.magnitude * (self._decay_rate ** age)
        mag = max(self._min, min(self._max, mag))

        return DriveSignal(
            key=signal.key,
            magnitude=mag,
            created_step=signal.created_step,
            source=signal.source,
        )

    def normalize(self, signals: List[DriveSignal]) -> List[DriveSignal]:
        if not signals:
            return []

        total = sum(s.magnitude for s in signals)
        if total <= 0:
            return signals

        return [
            DriveSignal(
                key=s.key,
                magnitude=s.magnitude / total,
                created_step=s.created_step,
                source=s.source,
            )
            for s in signals
        ]
