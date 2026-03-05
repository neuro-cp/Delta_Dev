from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ProposalGovernanceRequest:
    proposal: Any
    justification: str
