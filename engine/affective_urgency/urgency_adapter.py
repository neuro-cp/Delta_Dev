from __future__ import annotations

from typing import Optional

from engine.affective_urgency.urgency_signal import UrgencySignal
from engine.affective_urgency.urgency_policy import UrgencyPolicy
from engine.affective_urgency.urgency_trace import UrgencyTrace


class UrgencyAdapter:
    """
    Adapter layer for affective urgency.

    Bridges:
      - urgency signal
      - urgency policy
      - runtime observation
      - trace recording

    Produces a bounded urgency scalar.
    """

    def __init__(
        self,
        *,
        signal: UrgencySignal,
        policy: UrgencyPolicy,
        trace: Optional[UrgencyTrace] = None,
    ) -> None:
        self.signal = signal
        self.policy = policy
        self.trace = trace

        self._last_urgency: float = 0.0

    # --------------------------------------------------
    # Main interface
    # --------------------------------------------------

    def compute(
        self,
        *,
        time: float,
        step: int,
        dt: float,
        gate_relief: float,
        dominance_delta: float,
    ) -> float:
        """
        Compute urgency for the current step.

        Returns a bounded urgency scalar ∈ [0, 1].
        """

        # 1. Signal update (pure dynamics)
        raw_urgency = self.signal.step(dt)

        # 2. Policy gate (refusal-only)
        allowed, urgency, reason = self.policy.evaluate(
            urgency=raw_urgency,
            gate_relief=gate_relief,
            dominance_delta=dominance_delta,
        )

        if not allowed:
            urgency = 0.0

        self._last_urgency = urgency

        # 3. Trace (observational only)
        if self.trace is not None:
            self.trace.record(
                time=time,
                step=step,
                urgency=urgency,
                delta=dominance_delta,
                allowed=allowed,
                reason=reason,
                gate_relief=gate_relief,
            )

        return urgency

    # --------------------------------------------------
    # Introspection
    # --------------------------------------------------

    @property
    def last_urgency(self) -> float:
        return self._last_urgency

    def reset(self) -> None:
        self._last_urgency = 0.0
        self.signal.reset()
