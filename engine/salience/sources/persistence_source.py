# engine/salience/sources/persistence_source.py
from __future__ import annotations

from typing import Dict

from engine.salience.sources.salience_source import BaseSalienceSource


class PersistenceSource(BaseSalienceSource):
    """
    Persistence-based salience source.

    PURPOSE:
    - Maintain attention on already-salient channels
    - Smooth transient fluctuations
    - Prevent attention flicker

    BIOLOGICAL ANALOG:
    - Recurrent cortical bias
    - Short-term attentional inertia (NOT reward)

    DESIGN GUARANTEES:
    - Stateless
    - Self-referential only
    - Slow, conservative reinforcement
    """

    name = "persistence"

    # Must be weaker than competition
    max_delta = 0.02

    EPSILON = 1e-6

    def _compute_delta(
        self, observation: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Reinforce already-salient channels.

        Expected observation format:
            {
                channel_id: current_salience_value
            }

        Semantics:
        - Only reinforces existing salience
        - No new channels introduced
        - Zero-crossing channels ignored
        """

        if not observation:
            return {}

        deltas: Dict[str, float] = {}

        for channel_id, value in observation.items():
            v = float(value)

            # Ignore neutral or noise-level salience
            if abs(v) <= self.EPSILON:
                continue

            # Reinforce in same direction, very weakly
            deltas[channel_id] = v

        return deltas
