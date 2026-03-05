from dataclasses import dataclass


@dataclass(frozen=True)
class MomentumTrace:
    momentum_index: int
    sample_count: int
