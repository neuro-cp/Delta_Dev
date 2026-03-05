from dataclasses import dataclass


@dataclass(frozen=True)
class StabilityTrace:
    stability_index: int
    confidence: float
