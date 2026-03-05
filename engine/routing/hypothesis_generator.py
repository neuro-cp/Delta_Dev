from __future__ import annotations

from typing import Dict, List, Optional
from collections import defaultdict


class HypothesisGenerator:
    """
    Conservative hypothesis proposer.

    Responsibilities:
    - Observe cortical assemblies over time
    - Detect sustained, coherent activity
    - Propose hypothesis IDs (no routing, no gains)

    NON-RESPONSIBILITIES:
    - No learning
    - No salience injection
    - No BG interaction
    - No decision influence
    """

    def __init__(
        self,
        activity_threshold: float = 0.02,
        sustain_steps: int = 50,
        max_hypotheses: int = 8,
    ):
        self.activity_threshold = activity_threshold
        self.sustain_steps = sustain_steps
        self.max_hypotheses = max_hypotheses

        self._activity_counters: Dict[str, int] = defaultdict(int)
        self._active_hypotheses: Dict[str, str] = {}   # assembly_id → hypothesis_id
        self._hypothesis_index = 0

    # ---------------------------------------------------------
    # Observation
    # ---------------------------------------------------------

    def observe(self, assemblies: List) -> None:
        """
        Observe cortical assemblies (PopulationModel list).
        """
        for p in assemblies:
            aid = p.assembly_id
            act = float(getattr(p, "activity", 0.0))

            if act >= self.activity_threshold:
                self._activity_counters[aid] += 1
            else:
                self._activity_counters[aid] = 0

    # ---------------------------------------------------------
    # Proposal logic
    # ---------------------------------------------------------

    def propose(
        self,
        pressure: Optional[Dict[str, float]] = None,
    ) -> Dict[str, str]:
        """
        Return newly proposed hypotheses as:
            {assembly_id: hypothesis_id}

        pressure:
            Optional hypothesis pressure map (read-only, advisory).

        Does NOT register them automatically.
        """
        proposals: Dict[str, str] = {}

        if pressure is None:
            pressure = {}

        if len(self._active_hypotheses) >= self.max_hypotheses:
            return proposals

        for aid, count in list(self._activity_counters.items()):
            if count < self.sustain_steps:
                continue

            if aid in self._active_hypotheses:
                continue

            hid = self._new_hypothesis_id()
            proposals[aid] = hid
            self._active_hypotheses[aid] = hid

            if len(self._active_hypotheses) >= self.max_hypotheses:
                break

        return proposals

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def retire(self, hypothesis_id: str) -> None:
        """
        Remove a hypothesis from tracking.
        """
        for aid, hid in list(self._active_hypotheses.items()):
            if hid == hypothesis_id:
                del self._active_hypotheses[aid]

    def reset(self) -> None:
        self._activity_counters.clear()
        self._active_hypotheses.clear()
        self._hypothesis_index = 0

    # ---------------------------------------------------------
    # Introspection
    # ---------------------------------------------------------

    def snapshot(self) -> Dict[str, str]:
        return dict(self._active_hypotheses)

    # ---------------------------------------------------------
    # Internals
    # ---------------------------------------------------------

    def _new_hypothesis_id(self) -> str:
        self._hypothesis_index += 1
        return f"H{self._hypothesis_index}"
