# memory/semantic_promotion/promoted_semantic.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class PromotedSemantic:
    """
    Immutable declaration that a semantic pattern has been
    formally promoted to long-term semantic status.

    CONTRACT:
    - Offline only
    - Read-only
    - No runtime authority
    - No learning semantics
    - Safe to discard and rebuild from source artifacts

    This object represents *existence*, not influence.
    """

    # Identity
    semantic_id: str

    # Promotion provenance
    promotion_policy_version: str
    promotion_step: Optional[int]
    promotion_time: Optional[float]

    # Evidence lineage
    source_candidate_ids: List[str]
    supporting_episode_ids: List[int]

    # Stability summary (descriptive)
    recurrence_count: int
    persistence_span: int
    stability_classification: str

    # Optional metadata
    confidence_estimate: Optional[float] = None
    tags: Dict[str, Any] = None
    notes: Optional[str] = None
