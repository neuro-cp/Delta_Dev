from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class DiffAggregateInspectionView:
    """
    Inspection view for aggregated learning diffs.

    CONTRACT:
    - Read-only
    - Deterministic
    - Serializable
    """

    total_diffs: int
    semantic_term_add_counts: Dict[str, int]
    semantic_term_remove_counts: Dict[str, int]
    structural_signature_add_counts: Dict[Tuple, int]
    structural_signature_remove_counts: Dict[Tuple, int]
