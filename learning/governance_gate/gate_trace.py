from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceGateTrace:
    approved: bool
    reason: str
