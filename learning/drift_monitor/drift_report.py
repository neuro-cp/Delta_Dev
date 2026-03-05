from dataclasses import dataclass


@dataclass(frozen=True)
class DriftReport:
    drift_score: int
    trend: float
