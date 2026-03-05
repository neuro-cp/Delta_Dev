from __future__ import annotations

from typing import Optional

from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_policy import ValuePolicy
from engine.vta_value.value_trace import ValueTrace
from engine.vta_value.value_source import ValueProposal


class ValueEngine:
    """
    Central VTA value engine.

    CONTRACT:
    - Owns ValueSignal
    - Applies ValuePolicy
    - Emits ValueTrace
    - No decision authority
    """

    def __init__(
        self,
        *,
        signal: ValueSignal,
        policy: ValuePolicy,
        trace: ValueTrace,
    ) -> None:
        self._signal = signal
        self._policy = policy
        self._trace = trace

    def step(self, *, current_step: int) -> None:
        """
        Advance decay dynamics.

        CONTRACT:
        - No proposals required
        - Decay only
        """
        before = self._signal.value
        self._signal.decay(current_step=current_step)

        if self._signal.value != before:
            self._trace.record_decay(
                step=current_step,
                value=self._signal.value,
            )

    def apply_proposal(
        self,
        *,
        proposal: ValueProposal,
        current_step: int,
    ) -> bool:
        """
        Attempt to apply a value proposal.

        Returns True if accepted, False otherwise.
        """

        accepted, new_value, reason = self._policy.evaluate(
            current_value=self._signal.value,
            delta=proposal.delta,
            current_step=current_step,
        )

        self._trace.record_proposal(
            step=current_step,
            source=proposal.source,
            proposed_delta=proposal.delta,
            accepted=accepted,
            resulting_value=new_value if accepted else self._signal.value,
            reason=reason,
            note=proposal.note,
        )

        if not accepted:
            return False

        self._signal.set(new_value)
        return True

    @property
    def signal(self) -> ValueSignal:
        return self._signal
