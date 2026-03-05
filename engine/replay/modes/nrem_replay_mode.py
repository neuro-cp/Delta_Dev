from __future__ import annotations

from typing import Iterable

from engine.replay.modes.replay_mode import ReplayMode
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class NREMReplayMode(ReplayMode):
    """
    NREM replay mode.

    Characteristics:
    - Deterministic
    - Slower, chunked exposure
    - Preserves episode boundaries
    - No reordering, no noise

    NOTE:
    Chunking here is implemented as frame skipping
    (structural pacing, not information loss).
    """

    name = "nrem"

    def __init__(self, *, stride: int = 2) -> None:
        if stride < 1:
            raise ValueError("stride must be >= 1")
        self._stride = stride

    def iter_frames(
        self,
        frames: Iterable[ObservationFrame],
    ) -> Iterable[ObservationFrame]:
        for idx, frame in enumerate(frames):
            if idx % self._stride == 0:
                yield frame
