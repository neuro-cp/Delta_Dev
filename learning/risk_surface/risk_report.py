from dataclasses import dataclass


@dataclass(frozen=True)
class RiskReport:
    risk_index: int
    envelope_magnitude: int
    pressure: int
    trend: float
