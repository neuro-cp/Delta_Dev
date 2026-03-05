from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class WorkingItem:
    """
    Immutable working-memory item.

    CONTRACT:
    - Opaque payload
    - Time-local
    - No interpretation
    - No mutation after creation
    """

    key: str
    payload: Any
    strength: float
    created_step: int
    source: Optional[str] = None
