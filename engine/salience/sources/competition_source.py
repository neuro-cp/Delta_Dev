# engine/salience/sources/competition_source.py
from __future__ import annotations

from typing import Dict

from engine.salience.sources.salience_source import BaseSalienceSource


class CompetitionSource(BaseSalienceSource):
    """
    Competition-based salience source.

    PURPOSE:
    - Highlight relative dominance during competition
    - Increase attentional weight of leading channels
    - WITHOUT triggering or enforcing decisions

    BIOLOGICAL ANALOG:
    - Cortico-striatal contrast enhancement
    - Pre-decisional attentional bias

    DESIGN GUARANTEES:
    - Stateless
    - Relative (contrast-based)
    - Bounded and conservative
    """

    name = "competition"

    # Competition should be stronger than surprise,
    # but weaker than decision gating
    max_delta = 0.03

    EPSILON = 1e-6

    def _compute_delta(
        self, observation: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute salience deltas from competitive dominance.

        Expected observation format:
            {
                channel_id: dominance_value
            }

        Semantics:
        - Dominance values are assumed comparable
        - Only relative differences matter
        - Winner gets small positive salience
        - Losers get nothing (no punishment here)
        """

        if not observation or len(observation) < 2:
            return {}

        # Sort channels by dominance
        items = sorted(
            observation.items(),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        top_id, top_val = items[0]
        second_val = float(items[1][1])

        delta = float(top_val) - second_val

        if delta <= self.EPSILON:
            return {}

        # Linear contrast → salience
        return {
            top_id: delta
        }
