from dataclasses import dataclass


@dataclass(frozen=True)
class DriftTrace:
    drift_score: int
    trend: float
