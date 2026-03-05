from dataclasses import dataclass


@dataclass(frozen=True)
class RiskTrace:
    risk_index: int
    envelope_magnitude: int
    pressure: int
    trend: float
