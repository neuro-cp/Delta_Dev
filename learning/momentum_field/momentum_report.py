from dataclasses import dataclass


@dataclass(frozen=True)
class MomentumReport:
    momentum_index: int
    sample_count: int
