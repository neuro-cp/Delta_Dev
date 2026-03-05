# engine/salience/sources/surprise_source.py
from __future__ import annotations

from typing import Dict, Any

from engine.salience.sources.salience_source import BaseSalienceSource


class SurpriseSource(BaseSalienceSource):
    """
    Surprise-based salience source.

    PURPOSE:
    - Detect unexpected deviation in structurally meaningful signals
    - Highlight novelty prior to attention, value, or decision
    - Remain pre-semantic and pre-decisional

    BIOLOGICAL ANALOG:
    - Early cortical mismatch detection
    - Sensory / associative prediction error (pre-dopaminergic)

    DESIGN GUARANTEES:
    - Stateless
    - Symmetric (no valence)
    - Conservative magnitude
    - Ignores meta-time and control drift
    """

    name = "surprise"

    # Surprise must remain weaker than competition
    max_delta = 0.02

    # Minimum deviation required to count as surprise
    EPSILON = 1e-3

    # --------------------------------------------------
    # Expected semantic channels
    # --------------------------------------------------
    # These are produced by the observation layer, not runtime.
    #
    # Surprise does NOT infer baselines or differences itself.
    # It only interprets deviation signals handed to it.
    EXPECTED_KEYS = (
        "region_mass_delta",
        "region_activity_delta",
    )

    def _compute_delta(
        self, observation: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Compute salience deltas based on unexpected deviation.

        Surprise is defined as:
        - Deviation from an expected steady-state signal
        - Persisting beyond numerical noise
        - Structurally meaningful (not meta-time or control state)

        Interpretation:
        - Larger magnitude deviation → stronger surprise
        - Sign is ignored (surprise is unsigned)
        """

        deltas: Dict[str, float] = {}

        for key in self.EXPECTED_KEYS:
            delta_map = observation.get(key)
            if not isinstance(delta_map, dict):
                continue

            for region_key, deviation in delta_map.items():
                try:
                    mag = abs(float(deviation))
                except Exception:
                    continue

                if mag < self.EPSILON:
                    continue

                # Collapse anatomical source into a semantic channel
                channel_id = f"{key}:{region_key}"

                deltas[channel_id] = min(mag, self.max_delta)

        return deltas
