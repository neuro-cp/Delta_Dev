from dataclasses import dataclass

@dataclass(frozen=True)
class ConfidenceBand:
    center: float
    width: float
