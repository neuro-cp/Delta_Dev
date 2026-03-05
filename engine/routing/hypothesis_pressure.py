# engine/routing/hypothesis_pressure.py
from __future__ import annotations
from typing import Dict, Optional


class HypothesisPressure:
    """
    Read-only hypothesis formation pressure.

    Observes pre-decisional tension and emits proposal weights
    for assemblies that may warrant hypothesis candidates.

    Properties:
    - deterministic
    - bounded
    - reversible
    - no assignment, no routing, no learning
    """

    def __init__(
        self,
        min_gate_relief: float = 0.45,
        min_dominance_delta: float = 0.005,
        max_pressure: float = 1.0,
    ):
        self.min_gate_relief = float(min_gate_relief)
        self.min_dominance_delta = float(min_dominance_delta)
        self.max_pressure = float(max_pressure)

    def compute(
        self,
        *,
        gate_relief: float,
        dominance: Dict[str, float],
        assemblies: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute hypothesis pressure per assembly.

        Inputs:
        - gate_relief: current GPi relief (0..1)
        - dominance: channel -> dominance value
        - assemblies: assembly_id -> output/activity

        Returns:
        - assembly_id -> pressure weight (0..max_pressure)
        """

        # Preconditions: only operate in pre-decisional tension
        if gate_relief < self.min_gate_relief:
            return {}

        if len(dominance) < 2:
            return {}

        vals = sorted(dominance.values(), reverse=True)
        delta = vals[0] - vals[1]

        # If dominance is already decisive, do nothing
        if delta >= self.min_dominance_delta:
            return {}

        # Normalize pressure by how close we are to decision
        # Smaller delta → higher pressure
        tension = max(0.0, self.min_dominance_delta - delta)
        norm = self.min_dominance_delta
        pressure_scale = min(self.max_pressure, tension / max(norm, 1e-6))

        out: Dict[str, float] = {}

        for aid, activity in assemblies.items():
            if activity <= 0.0:
                continue

            # Activity-weighted, bounded pressure
            p = min(self.max_pressure, pressure_scale * activity)
            if p > 0.0:
                out[aid] = p

        return out
