from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass(frozen=True)
class PromotionCandidate:
    """
    Immutable declaration that a semantic pattern satisfies
    a specific promotion policy.

    This object:
    - carries NO authority
    - does NOT cause promotion
    - does NOT create memory
    - is safe to discard and recompute

    PromotionCandidates are advisory artifacts only.
    """

    # Identity
    semantic_id: str
    pattern_type: str

    # Policy context
    policy_version: str
    schema_version: str

    # Evidence summary (descriptive only)
    supporting_episode_ids: List[int]
    recurrence_count: int
    persistence_span: int

    # Stability diagnostics
    stability_classification: str
    drift_consistent: bool

    # Disqualification checks (explicit)
    disqualified: bool
    disqualification_reasons: List[str] = field(default_factory=list)

    # Optional descriptive metadata
    confidence_estimate: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
