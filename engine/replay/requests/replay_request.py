from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReplayRequest:
    """
    A request to CONSIDER replay.

    This object carries no authority.
    It does not guarantee replay will occur.

    ReplayRequest exists to express *when* replay may be desirable,
    not *what* replay means or *how* it is executed.
    """

    # Human- or system-readable reason (e.g. "manual", "idle", "stress")
    reason: str

    # Logical time or step at which the request was made
    requested_step: Optional[int] = None

    # Optional bounded urgency hint (scheduler may ignore)
    urgency: Optional[float] = None

    # Optional origin metadata (inspection only)
    # e.g. "sleep_orchestrator", "manual", "test"
    origin: Optional[str] = None
