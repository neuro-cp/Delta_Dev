from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ProposalGovernanceRecord:
    accepted: bool
    request_snapshot: Any
    reason: str
