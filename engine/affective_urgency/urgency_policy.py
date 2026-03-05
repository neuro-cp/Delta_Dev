from __future__ import annotations


class UrgencyPolicy:
    """
    Policy gate for affective urgency.

    Responsibilities:
    - Decide whether urgency is allowed this step
    - Enforce hard safety bounds
    - Never amplify urgency
    - Never trigger decisions
    """

    def __init__(
        self,
        *,
        allow: bool = True,
        min_gate_relief: float = 0.0,
        max_gate_relief: float = 1.0,
        max_urgency: float = 1.0,
    ) -> None:
        self.allow = bool(allow)
        self.min_gate_relief = float(min_gate_relief)
        self.max_gate_relief = float(max_gate_relief)
        self.max_urgency = float(max_urgency)

    # --------------------------------------------------
    # Core policy
    # --------------------------------------------------

    def evaluate(
        self,
        *,
        urgency: float,
        gate_relief: float,
        dominance_delta: float,
    ) -> tuple[bool, float, str]:
        """
        Decide whether urgency is permitted this step.

        Returns:
        (allowed, urgency, reason)

        Notes:
        - urgency is never increased here
        - dominance_delta is observed but not acted on (future hook)
        """

        if not self.allow:
            return False, urgency, "policy_disabled"

        if urgency >= self.max_urgency:
            return False, urgency, "urgency_saturated"

        if gate_relief < self.min_gate_relief:
            return False, urgency, "gate_too_closed"

        if gate_relief > self.max_gate_relief:
            return False, urgency, "gate_overrelieved"

        # Allowed: urgency passes through unchanged
        return True, urgency, "conditions_met"

    # --------------------------------------------------
    # Introspection
    # --------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "allow": self.allow,
            "min_gate_relief": self.min_gate_relief,
            "max_gate_relief": self.max_gate_relief,
            "max_urgency": self.max_urgency,
        }
