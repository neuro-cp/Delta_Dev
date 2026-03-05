from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class GovernanceEnablementRecord:
    accepted: bool
    request_snapshot: Any
    reason: str
