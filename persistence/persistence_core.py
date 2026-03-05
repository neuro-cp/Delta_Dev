# persistence/persistence_core.py
from __future__ import annotations

from typing import Dict

from persistence.traces import ExponentialTrace


class BasalGangliaPersistence:
    """
    Short-lived persistence of recent striatal dominance.

    FUNCTIONAL ROLE:
    - Maintain a transient eligibility-like trace for recent winners
    - Provide a small, bounded additive bias to future competition
    - Act as inertia / stabilization, NOT learning or habit

    HARD GUARANTEES:
    - No learning
    - No plasticity
    - No parameter writes
    - Fully bounded, exponentially decaying
    """

    def __init__(
        self,
        decay_tau: float = 30.0,
        bias_gain: float = 0.15,
        epsilon: float = 1e-9,
        enable_diagnostics: bool = False,
    ):
        # Per-assembly traces
        self.traces: Dict[str, ExponentialTrace] = {}

        self.decay_tau = float(decay_tau)
        self.bias_gain = float(bias_gain)
        self.epsilon = float(epsilon)

        # Optional observability
        self.enable_diagnostics = bool(enable_diagnostics)
        self.last_total_bias: float = 0.0
        self.last_active_traces: int = 0

    # ------------------------------------------------------------
    # Trace management
    # ------------------------------------------------------------

    def ensure_trace(self, assembly_id: str) -> None:
        aid = str(assembly_id)
        if aid not in self.traces:
            self.traces[aid] = ExponentialTrace(decay_tau=self.decay_tau)

    # ------------------------------------------------------------
    # Dynamics
    # ------------------------------------------------------------

    def step(self, dt: float) -> None:
        """
        Advance all traces and remove near-zero entries.
        """
        if not self.traces:
            return

        dead = []
        for aid, trace in self.traces.items():
            trace.step(dt)
            if abs(getattr(trace, "value", 0.0)) < self.epsilon:
                dead.append(aid)

        for aid in dead:
            del self.traces[aid]

    # ------------------------------------------------------------
    # Reinforcement
    # ------------------------------------------------------------

    def reinforce(self, assembly_id: str, amount: float) -> None:
        """
        Additively reinforce a trace.

        NOTE:
        - Caller is responsible for deciding what "winner" means.
        - This function is intentionally dumb and bounded.
        """
        if amount == 0.0:
            return

        self.ensure_trace(assembly_id)
        self.traces[str(assembly_id)].reinforce(float(amount))

    # ------------------------------------------------------------
    # Readout
    # ------------------------------------------------------------

    def get_bias(self, assembly_id: str) -> float:
        """
        Return additive bias for a single assembly.

        Intended to be aggregated at the CHANNEL level by caller.
        """
        trace = self.traces.get(str(assembly_id))
        if not trace:
            return 0.0

        return float(getattr(trace, "value", 0.0)) * self.bias_gain

    def get_all_biases(self) -> Dict[str, float]:
        """
        Read-only snapshot of current biases (post gain).
        Useful for diagnostics and testing.
        """
        out = {}
        total = 0.0

        for aid, trace in self.traces.items():
            val = float(getattr(trace, "value", 0.0)) * self.bias_gain
            if abs(val) > 0.0:
                out[aid] = val
                total += abs(val)

        if self.enable_diagnostics:
            self.last_total_bias = total
            self.last_active_traces = len(out)

        return out

    def dump(self) -> Dict[str, float]:
        """
        Raw trace values (pre gain).
        Debug-only.
        """
        return {aid: float(getattr(t, "value", 0.0)) for aid, t in self.traces.items()}

    def clear(self) -> None:
        """
        Hard reset (used only for test isolation).
        """
        self.traces.clear()
        self.last_total_bias = 0.0
        self.last_active_traces = 0
