from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReplayExecutionConfig:
    """
    Configuration for replay execution.

    This object selects HOW replay is executed,
    not WHEN or WHAT is replayed.

    It is:
    - Offline
    - Non-authoritative
    - Safe to discard
    """

    # Name of the replay mode ("wake", "nrem", "rem")
    mode: str = "wake"

    # Optional parameters passed to the replay mode
    stride: Optional[int] = None
    seed: Optional[int] = None
