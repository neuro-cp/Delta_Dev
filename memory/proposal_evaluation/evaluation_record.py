from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvaluationRecord:
    proposal_id: str
    evaluator_id: str
    policy_id: str
    accepted: bool
    rationale: Optional[str]
