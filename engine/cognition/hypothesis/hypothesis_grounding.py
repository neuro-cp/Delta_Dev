from __future__ import annotations

from typing import Dict, Iterable, Tuple

from engine.cognition.hypothesis import Hypothesis
from engine.population_model import PopulationModel


class HypothesisGrounding:
    """
    Phase 6.4: Read-only grounding of hypotheses in assembly activity.

    Scope:
    - Hypotheses accumulate support from observed assembly output
    - Observation only, no feedback
    - Deterministic and bounded

    Forbidden:
    - Assembly modification
    - Salience or routing bias
    - Decision or memory influence
    """

    def __init__(
        self,
        *,
        support_gain: float = 1.0,
        max_support: float = 10.0,
    ) -> None:
        self.support_gain = float(support_gain)
        self.max_support = float(max_support)

    def step(
        self,
        *,
        hypotheses: Iterable[Hypothesis],
        observed_assemblies: Iterable[PopulationModel],
    ) -> None:
        """
        Accumulate hypothesis support from current assembly outputs.

        NOTE:
        - All hypotheses observe the same assemblies
        - Later phases may introduce selectivity
        """
        total_signal = 0.0

        for a in observed_assemblies:
            # read-only observation
            total_signal += a.output()

        for h in hypotheses:
            if not h.active:
                continue

            h.support += self.support_gain * total_signal

            if h.support > self.max_support:
                h.support = self.max_support
