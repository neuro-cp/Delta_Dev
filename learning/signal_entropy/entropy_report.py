from dataclasses import dataclass


@dataclass(frozen=True)
class EntropyReport:
    entropy_index: float
    signal_count: int
