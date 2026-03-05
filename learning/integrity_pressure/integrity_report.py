from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrityReport:
    integrity_pressure: int
    trend: float
    confidence: float
