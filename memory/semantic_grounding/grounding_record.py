from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class SemanticRegionalGrounding:
    """
    Immutable, descriptive grounding record.

    This object represents a static association between a
    *promoted semantic entity* and one or more neural regions.

    CONTRACT:
    - Pure data
    - No authority
    - No execution
    - No learning
    - No inference
    """

    # Must correspond to PromotedSemantic.semantic_id
    semantic_id: str

    # Set of region IDs (Phase-14 scoped only)
    grounded_regions: FrozenSet[str]

    # Optional human-readable explanation
    notes: Optional[str] = None

    # --------------------------------------------------
    # Invariants (by contract, not enforcement here)
    # --------------------------------------------------
    #
    # - No numeric fields
    # - No weights
    # - No priorities
    # - No timestamps
    # - No decay
    # - No population or assembly references
    #
    # Validation is external and explicit.
