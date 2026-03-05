from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional
import time


@dataclass(frozen=True)
class ContextTrace:
    """
    Immutable context memory trace.

    A trace represents a snapshot of relevance under a given context,
    NOT a fact, belief, or decision.

    DESIGN CONSTRAINTS:
    - Immutable (no in-place mutation)
    - No references to runtime, BG, PFC, dopamine, etc.
    - No learning logic
    - No sequencing assumptions
    """

    # -----------------------------
    # Identity
    # -----------------------------
    trace_id: str

    # -----------------------------
    # Context signature
    # -----------------------------
    # Arbitrary key → value tags describing the situation
    # e.g. {"task": "foraging", "valence": "positive"}
    context: Dict[str, str]

    # -----------------------------
    # Strength & salience
    # -----------------------------
    strength: float

    # -----------------------------
    # Temporal metadata
    # -----------------------------
    created_at: float = field(default_factory=lambda: time.time())

    # -----------------------------
    # Optional provenance
    # -----------------------------
    source_region: Optional[str] = None
    source_channel: Optional[str] = None

    # -----------------------------
    # Read helpers
    # -----------------------------
    def matches(self, query: Dict[str, str]) -> bool:
        """
        Return True if this trace matches all provided context keys.

        Matching is exact and conjunctive.
        No fuzzy logic here — policy handles that later.
        """
        for k, v in query.items():
            if self.context.get(k) != v:
                return False
        return True

    def age(self, now: Optional[float] = None) -> float:
        """
        Age of the trace in seconds.
        """
        t = now if now is not None else time.time()
        return max(0.0, t - self.created_at)
