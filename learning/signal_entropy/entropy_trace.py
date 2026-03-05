from dataclasses import dataclass


@dataclass(frozen=True)
class EntropyTrace:
    entropy_index: float
    signal_count: int
