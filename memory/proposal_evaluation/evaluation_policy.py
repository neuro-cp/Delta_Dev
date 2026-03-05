from __future__ import annotations


class EvaluationPolicy:
    """
    Pure declarative policy marker.
    Carries no logic, thresholds, or magnitudes.
    """

    def __init__(self, policy_id: str) -> None:
        self.policy_id = policy_id
