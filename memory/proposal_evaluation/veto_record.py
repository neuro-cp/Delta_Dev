from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VetoRecord:
    proposal_id: str
    veto_policy_id: str
    vetoed: bool
    rationale: Optional[str]
