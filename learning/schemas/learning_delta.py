from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class LearningDelta:
    """
    Descriptive, non-applied parameter or structure adjustment.

    CONTRACT:
    - Immutable
    - No execution semantics
    - No implicit application
    """

    target: str               # e.g. "semantic_frequency", "structural_weight"
    delta_type: str           # "additive", "multiplicative", "structural"
    magnitude: float          # bounded, unsigned interpretation left to policy
    metadata: Dict[str, Any]
