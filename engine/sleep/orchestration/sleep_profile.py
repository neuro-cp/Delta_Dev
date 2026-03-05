from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal


ReplayMode = Literal["wake", "nrem", "rem"]


@dataclass(frozen=True)
class SleepProfile:
    """
    Describes what kind of replay is permitted.
    """

    name: str

    allowed_replay_modes: List[ReplayMode]

    max_episodes: int

    description: str
