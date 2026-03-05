from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationTrace:
    escalation_level: str
    pressure: int
    trend: float
