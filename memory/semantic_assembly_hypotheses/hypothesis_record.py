from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class SemanticAssemblyHypothesis:
    """
    Immutable, descriptive hypothesis linking a promoted
    semantic to assemblies within a single region.

    CONTRACT:
    - Pure data
    - No numeric fields
    - No confidence, weight, or probability
    - No execution or authority
    """

    # Must correspond to PromotedSemantic.semantic_id
    semantic_id: str

    # Region in which the assemblies reside
    region_id: str

    # Opaque assembly identifiers (symbolic only)
    assembly_ids: FrozenSet[str]

    # Optional human-readable rationale
    rationale: Optional[str] = None
