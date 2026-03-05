# memory/semantic_promotion/promoted_semantic_registry.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from memory.semantic_promotion.promoted_semantic import PromotedSemantic


@dataclass(frozen=True)
class PromotedSemanticRegistry:
    """
    Read-only registry of promoted semantic patterns.

    CONTRACT:
    - Offline only
    - Immutable after construction
    - No promotion logic
    - No runtime authority
    - No learning semantics
    - Safe to discard and rebuild

    This registry is the sole canonical owner of
    PromotedSemantic artifacts.
    """

    _by_id: Dict[str, PromotedSemantic]

    @classmethod
    def build(
        cls,
        *,
        promoted_semantics: Iterable[PromotedSemantic],
    ) -> PromotedSemanticRegistry:
        by_id: Dict[str, PromotedSemantic] = {}

        for semantic in promoted_semantics:
            if semantic.semantic_id in by_id:
                raise ValueError(
                    f"Duplicate promoted semantic_id: {semantic.semantic_id}"
                )
            by_id[semantic.semantic_id] = semantic

        return cls(_by_id=by_id)

    def get(self, semantic_id: str) -> PromotedSemantic | None:
        return self._by_id.get(semantic_id)

    def all(self) -> List[PromotedSemantic]:
        return list(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self):
        return iter(self._by_id.values())
