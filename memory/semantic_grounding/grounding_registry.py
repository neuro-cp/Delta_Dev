from __future__ import annotations

from typing import Dict, Iterable, Optional

from memory.semantic_grounding.grounding_record import (
    SemanticRegionalGrounding,
)


class SemanticGroundingRegistry:
    """
    Read-only registry for semantic → regional grounding records.

    This registry:
    - owns grounding records
    - provides lookup by semantic_id
    - performs no inference
    - performs no resolution
    - performs no prioritization

    It is storage, not logic.
    """

    def __init__(
        self,
        records: Iterable[SemanticRegionalGrounding],
    ) -> None:
        self._by_semantic_id: Dict[str, SemanticRegionalGrounding] = {
            r.semantic_id: r for r in records
        }

    # --------------------------------------------------
    # Read-only accessors
    # --------------------------------------------------

    def get(
        self, semantic_id: str
    ) -> Optional[SemanticRegionalGrounding]:
        return self._by_semantic_id.get(semantic_id)

    def all(self) -> Iterable[SemanticRegionalGrounding]:
        return self._by_semantic_id.values()

    def __len__(self) -> int:
        return len(self._by_semantic_id)
