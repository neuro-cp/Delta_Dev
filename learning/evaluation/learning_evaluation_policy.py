from __future__ import annotations

from typing import Tuple


class LearningEvaluationPolicy:
    """
    Policy defining whether learning is allowed.

    CONTRACT:
    - Pure logic
    - Deterministic
    - No mutation
    - Structural proposals require stronger evidence
    """

    MIN_TOTAL_DIFFS: int = 1
    MIN_STRUCTURAL_DIFFS: int = 2  # stricter threshold for structural patterns

    @classmethod
    def evaluate(
        cls,
        *,
        total_diffs: int,
        structural_diffs: int = 0,  # optional, backward compatible
    ) -> Tuple[bool, Tuple[str, ...]]:
        reasons = []

        if total_diffs < cls.MIN_TOTAL_DIFFS:
            reasons.append("insufficient_evidence")

        # Additional constraint only applies if structural diffs are present
        if structural_diffs > 0 and structural_diffs < cls.MIN_STRUCTURAL_DIFFS:
            reasons.append("insufficient_structural_evidence")

        allowed = not reasons
        return allowed, tuple(reasons)