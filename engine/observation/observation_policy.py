from __future__ import annotations
from typing import Dict


class ObservationPolicy:
    """
    Declarative thresholds for observational events.
    No runtime access, no mutation.
    """

    MASS_DELTA_THRESHOLD: float = 0.2
    FRACTION_ACTIVE_THRESHOLD: float = 0.15

    @classmethod
    def should_emit_mass_shift(cls, delta: float) -> bool:
        return abs(delta) >= cls.MASS_DELTA_THRESHOLD

    @classmethod
    def should_emit_fraction_change(cls, delta: float) -> bool:
        return abs(delta) >= cls.FRACTION_ACTIVE_THRESHOLD
