# engine/salience/pre_decision_adaptation/record.py

from dataclasses import dataclass


@dataclass(frozen=True)
class PSMRecord:
    """
    Summary of one deliberation episode.

    This record captures *difficulty*, not outcome.
    It must not encode reward, correctness, or decision authority.
    """

    # Identifier for the context or situation.
    # Can be coarse at v0 (even a constant), refined later.
    context_id: str

    # Cost of deliberation (e.g. steps between gate-open and decision,
    # or total pre-decision window if no decision occurred).
    deliberation_cost: float

    # Scalar measure of instability during deliberation.
    # Examples: variance of Δ-dominance, number of sign flips, etc.
    instability: float

    # Runtime step when deliberation effectively began
    step_start: int

    # Runtime step when decision occurred or deliberation ended
    step_end: int
