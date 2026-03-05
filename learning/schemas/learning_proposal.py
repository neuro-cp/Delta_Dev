from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class LearningProposal:
    """
    Immutable learning suggestion.

    This object:
    - carries NO authority
    - does NOT apply changes
    - is replay-derived
    """

    proposal_id: str
    source_replay_id: str

    deltas: List["LearningDelta"]

    confidence: float
    justification: Dict[str, Any]

    bounded: bool
    replay_consistent: bool
    audit_tags: List[str] = field(default_factory=list)
