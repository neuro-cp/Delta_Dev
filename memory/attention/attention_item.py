from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AttentionItem:
    """
    Immutable attention item.

    CONTRACT:
    - Identifies an attention target
    - Carries a gain weight
    - Decays over time
    - No interpretation
    """

    key: str
    gain: float
    created_step: int
    source: Optional[str] = None
