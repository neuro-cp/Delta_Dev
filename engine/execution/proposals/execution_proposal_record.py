from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ExecutionProposalRecord:
    accepted: bool
    proposal_snapshot: Any
    reason: str
