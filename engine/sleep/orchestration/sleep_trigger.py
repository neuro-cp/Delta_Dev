from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SleepTriggerType = Literal[
    "manual",
    "circadian",
    "idle",
    "overload",
    "instability",
]


@dataclass(frozen=True)
class SleepTrigger:
    """
    Describes why sleep/replay is being considered.
    """

    trigger_type: SleepTriggerType
    source: str  # e.g. "user", "system", "policy"
