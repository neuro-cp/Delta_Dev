from __future__ import annotations

from typing import Iterable

from engine.replay.modes.replay_mode import ReplayMode
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class WakeReplayMode(ReplayMode):
    """
    Wake replay mode.

    Characteristics:
    - Deterministic
    - Full fidelity
    - Preserves original order
    - Control condition for all other modes
    """

    name = "wake"

    def iter_frames(
        self,
        frames: Iterable[ObservationFrame],
    ) -> Iterable[ObservationFrame]:
        for frame in frames:
            yield frame
