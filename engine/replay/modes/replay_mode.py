from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class ReplayMode(ABC):
    """
    Abstract base class for replay execution modes.

    A ReplayMode controls HOW observation frames are presented
    to cognition during replay execution.

    It does NOT:
    - Select episodes
    - Modify ReplayPlan
    - Write memory
    - Promote semantics
    - Influence runtime
    """

    name: str = "base"

    @abstractmethod
    def iter_frames(
        self,
        frames: Iterable[ObservationFrame],
    ) -> Iterable[ObservationFrame]:
        """
        Yield observation frames in the order and cadence
        defined by this replay mode.
        """
        raise NotImplementedError
