from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass(frozen=True)
class SignalSnapshot:
    """
    Offline snapshot of modulatory signals at a single timestep.

    This object represents a READ-ONLY observation derived
    from trace data after runtime execution.

    CONTRACT:
    - Descriptive only
    - Offline only
    - No authority
    - No mutation
    - No semantics

    It may be:
    - narrated
    - inspected
    - aggregated
    - replayed

    It MUST NOT:
    - influence runtime
    - encode intent
    - imply meaning
    - trigger learning
    """

    # --------------------------------------------------
    # Temporal anchor
    # --------------------------------------------------

    step: int

    # --------------------------------------------------
    # Modulatory signals (optional, sparse by design)
    # --------------------------------------------------

    # Salience: deviation / surprise (unsigned, bounded)
    salience: Optional[float] = None

    # Value: slow motivational bias (signed or unsigned, policy-defined)
    value: Optional[float] = None

    # Urgency: time pressure / drive intensity
    urgency: Optional[float] = None

    # --------------------------------------------------
    # Presence helpers
    # --------------------------------------------------

    def is_nonbaseline(self) -> bool:
        """
        Return True if at least one signal is present and non-zero.
        """
        return any(
            v is not None and v != 0.0
            for v in (self.salience, self.value, self.urgency)
        )

    def has_any(self) -> bool:
        """
        Alias for is_nonbaseline(), provided for semantic clarity
        in narration and inspection code.
        """
        return self.is_nonbaseline()

    # --------------------------------------------------
    # Serialization helpers
    # --------------------------------------------------

    def as_dict(self) -> Dict[str, float]:
        """
        Return a compact dict of present signals.

        Only signals explicitly present (not None) are included.
        Zero-valued signals may be included if present by design.
        """
        out: Dict[str, float] = {}

        if self.salience is not None:
            out["salience"] = self.salience
        if self.value is not None:
            out["value"] = self.value
        if self.urgency is not None:
            out["urgency"] = self.urgency

        return out
