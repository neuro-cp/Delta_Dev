from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DriveSignal:
    """
    Immutable drive signal.

    CONTRACT:
    - Scalar magnitude
    - Slow-changing
    - No semantics
    """

    key: str
    magnitude: float
    created_step: int
    source: Optional[str] = None
