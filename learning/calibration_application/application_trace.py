from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationApplicationTrace:
    proposed_adjustment: int
    allowed_adjustment: int
    applied_adjustment: int
    was_clamped: bool
