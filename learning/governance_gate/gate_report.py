from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceGateReport:
    approved: bool
    reason: str
