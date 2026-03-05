from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.sleep.orchestration.sleep_trigger import SleepTrigger


@dataclass(frozen=True)
class SleepRequest:
    """
    Request to consider entering a sleep/replay cycle.
    """

    trigger: SleepTrigger

    requested_step: int

    urgency: Optional[float] = None
