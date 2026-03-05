from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationReport:
    escalation_level: str
    pressure: int
    trend: float
