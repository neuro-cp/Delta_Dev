from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from memory.semantic_grounding.grounding_registry import (
    SemanticGroundingRegistry,
)


@dataclass(frozen=True)
class SemanticRegionalGroundingView:
    """
    Inspection-only, human-facing grounding view.

    This view:
    - is descriptive only
    - carries no authority
    - performs no inference
    """

    semantic_id: str
    grounded_regions: List[str]
    notes: Optional[str]


class SemanticGroundingInspectionAdapter:
    """
    Adapter to expose semantic grounding through inspection output.

    CONTRACT:
    - Read-only
    - Deterministic
    - No mutation
    - No runtime coupling
    """

    def build_views(
        self,
        *,
        grounding_registry: SemanticGroundingRegistry,
    ) -> Dict[str, SemanticRegionalGroundingView]:
        views: Dict[str, SemanticRegionalGroundingView] = {}

        for record in grounding_registry.all():
            views[record.semantic_id] = SemanticRegionalGroundingView(
                semantic_id=record.semantic_id,
                grounded_regions=sorted(record.grounded_regions),
                notes=record.notes,
            )

        return views
