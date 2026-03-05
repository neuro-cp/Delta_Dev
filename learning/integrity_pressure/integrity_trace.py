from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrityTrace:
    integrity_pressure: int
    trend: float
    confidence: float
