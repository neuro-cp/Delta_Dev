from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceRecordTrace:
    fragility_index: float
    allowed_adjustment: int
    max_adjustment: int
    proposed_adjustment: int
    applied_adjustment: int
    was_clamped: bool
