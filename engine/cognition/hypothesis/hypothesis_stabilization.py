from __future__ import annotations

from typing import Dict, Iterable, List

from engine.cognition.hypothesis import Hypothesis


class HypothesisStabilization:
    """
    Phase 6.5: Detect hypothesis stabilization.

    A hypothesis is considered stabilized when:
    - it remains active
    - its activation stays above a threshold
    - for a fixed number of consecutive steps

    This module:
    - does NOT alter hypotheses
    - does NOT influence runtime
    - emits auditable stabilization events only
    """

    def __init__(
        self,
        *,
        activation_threshold: float = 0.1,
        sustain_steps: int = 5,
    ) -> None:
        if sustain_steps <= 0:
            raise ValueError("sustain_steps must be positive")

        self.activation_threshold = float(activation_threshold)
        self.sustain_steps = int(sustain_steps)

        # internal counters (ephemeral, not persisted)
        self._counters: Dict[str, int] = {}

    # ------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------

    def step(self, hypotheses: Iterable[Hypothesis]) -> List[Dict]:
        """
        Observe hypotheses and return stabilization events.

        Returns:
            List of event dicts (may be empty).
        """
        events: List[Dict] = []

        for h in hypotheses:
            hid = h.hypothesis_id

            if h.active and h.activation >= self.activation_threshold:
                self._counters[hid] = self._counters.get(hid, 0) + 1
            else:
                self._counters[hid] = 0

            if self._counters[hid] == self.sustain_steps:
                events.append(
                    {
                        "event": "hypothesis_stabilized",
                        "hypothesis_id": hid,
                        "activation": h.activation,
                        "age": h.age,
                    }
                )

        return events
