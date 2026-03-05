from dataclasses import dataclass


@dataclass(frozen=True)
class StabilityReport:
    stability_index: int
    confidence: float
