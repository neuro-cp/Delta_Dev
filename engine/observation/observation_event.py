from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ObservationEvent:
    """
    Immutable observational fact emitted from runtime inspection.

    This object:
    - Contains no logic
    - Carries no authority
    - Is safe to store, discard, or replay
    """

    step: int
    region: str
    event_type: str
    payload: Dict[str, Any]
