from __future__ import annotations

from typing import Iterable

from engine.cognition.hypothesis import Hypothesis


class HypothesisCompetition:
    """
    Phase 6.3: Internal hypothesis competition.

    Scope:
    - Mutual suppression between active hypotheses
    - Soft competition (no hard winner)
    - No runtime influence
    - No memory emission

    Forbidden:
    - Region or assembly access
    - Salience, routing, or latch interaction
    """

    def __init__(
        self,
        *,
        competition_gain: float = 0.1,
        min_activation: float = 0.0,
    ) -> None:
        if competition_gain < 0.0:
            raise ValueError("competition_gain must be non-negative")

        self.competition_gain = float(competition_gain)
        self.min_activation = float(min_activation)

    # ------------------------------------------------------------
    # Core competition logic
    # ------------------------------------------------------------

    def step(self, hypotheses: Iterable[Hypothesis]) -> None:
        """
        Apply mutual suppression among active hypotheses.

        Suppression is proportional to the summed activation
        of competing hypotheses.
        """
        active = [h for h in hypotheses if h.active]

        if len(active) <= 1:
            return

        total_activation = sum(h.activation for h in active)

        for h in active:
            suppression = self.competition_gain * (total_activation - h.activation)
            h.activation -= suppression

            if h.activation <= self.min_activation:
                h.activation = 0.0
                h.active = False
