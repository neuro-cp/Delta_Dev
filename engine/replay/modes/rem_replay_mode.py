from __future__ import annotations

import random
from typing import Iterable, List

from engine.replay.modes.replay_mode import ReplayMode
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class REMReplayMode(ReplayMode):
    """
    REM replay mode.

    Characteristics:
    - Order-permuted
    - Boundary-relaxed
    - Deterministic under seed
    - No memory writes, no semantics

    This introduces controlled disorder WITHOUT authority.
    """

    name = "rem"

    def __init__(self, *, seed: int | None = None) -> None:
        self._seed = seed

    def iter_frames(
        self,
        frames: Iterable[ObservationFrame],
    ) -> Iterable[ObservationFrame]:
        frame_list: List[ObservationFrame] = list(frames)

        rng = random.Random(self._seed)
        rng.shuffle(frame_list)

        for frame in frame_list:
            yield frame
