from __future__ import annotations

from dataclasses import dataclass
from typing import List

from engine.sleep.orchestration.sleep_profile import ReplayMode


@dataclass(frozen=True)
class SleepDecision:
    """
    Auditable result of sleep orchestration.
    """

    profile_name: str

    selected_replay_modes: List[ReplayMode]

    episode_budget: int

    justification: str
