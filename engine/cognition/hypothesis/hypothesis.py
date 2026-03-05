from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class Hypothesis:
    """
    Cognitive hypothesis placeholder.

    Phase 6.1 scope:
    - Existence only
    - No dynamics
    - No influence
    - No semantic content

    This object represents a *potential* internal interpretation
    that may later gain persistence, support, and competition.
    """

    # -------------------------
    # Identity
    # -------------------------

    hypothesis_id: str
    created_step: int

    # -------------------------
    # State (inert for now)
    # -------------------------

    activation: float = 0.0
    support: float = 0.0
    age: int = 0
    active: bool = True

    # -------------------------
    # Introspection
    # -------------------------

    def to_dict(self) -> Dict[str, object]:
        """
        Serialize hypothesis to a stable, audit-safe dict.
        """
        return asdict(self)
