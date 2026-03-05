from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass(frozen=True)
class LearningSessionReport:
    """
    Immutable summary of a learning session execution.

    CONTRACT:
    - Descriptive only
    - No authority
    - No application semantics
    - Safe to discard and recompute
    - May include governance observation artifacts
    """

    replay_id: str
    proposal_ids: List[str]
    proposal_count: int
    rejected_count: int
    audit_passed: bool
    audit_notes: Optional[str] = None

    # Governance (Observational Only)
    governance_record: Optional[Any] = None
    governance_approved: Optional[bool] = None