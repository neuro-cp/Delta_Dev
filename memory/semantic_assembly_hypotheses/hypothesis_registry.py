from __future__ import annotations

from typing import Dict, Iterable, List

from memory.semantic_assembly_hypotheses.hypothesis_record import (
    SemanticAssemblyHypothesis,
)


class SemanticAssemblyHypothesisRegistry:
    """
    Read-only container for semantic → assembly hypotheses.

    Responsibilities:
    - Store hypotheses
    - Enumerate hypotheses
    - Provide lookup by semantic_id

    Explicitly forbidden:
    - Inference
    - Scoring
    - Merging
    - Conflict resolution
    """

    def __init__(
        self,
        hypotheses: Iterable[SemanticAssemblyHypothesis],
    ) -> None:
        self._by_semantic_id: Dict[str, List[SemanticAssemblyHypothesis]] = {}

        for h in hypotheses:
            self._by_semantic_id.setdefault(h.semantic_id, []).append(h)

    def for_semantic(
        self, semantic_id: str
    ) -> List[SemanticAssemblyHypothesis]:
        return list(self._by_semantic_id.get(semantic_id, []))

    def all(self) -> Iterable[SemanticAssemblyHypothesis]:
        for group in self._by_semantic_id.values():
            for h in group:
                yield h
