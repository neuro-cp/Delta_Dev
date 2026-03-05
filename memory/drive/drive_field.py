from __future__ import annotations

from typing import List, Iterable

from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy


class DriveField:
    """
    Active drive field.

    CONTRACT:
    - Holds DriveSignals
    - Applies decay and normalization
    - Produces bias suggestions only
    """

    def __init__(
        self,
        *,
        policy: DrivePolicy,
    ) -> None:
        self._policy = policy
        self._signals: List[DriveSignal] = []

    def signals(self) -> List[DriveSignal]:
        return list(self._signals)

    def ingest(self, signals: Iterable[DriveSignal]) -> None:
        for s in signals:
            self._signals.append(s)

    def step(self, *, current_step: int) -> None:
        decayed = [
            self._policy.decay(s, current_step=current_step)
            for s in self._signals
        ]

        self._signals = self._policy.normalize(decayed)
