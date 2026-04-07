
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from memory.semantic_promotion.promoted_semantic import PromotedSemantic


@dataclass(frozen=True)
class PromotedSemanticRegistry:

    _by_id: Dict[str, PromotedSemantic]

    @classmethod
    def build(
        cls,
        *,
        promoted_semantics: Iterable[PromotedSemantic],
    ) -> PromotedSemanticRegistry:

        by_id: Dict[str, PromotedSemantic] = {}

        for semantic in promoted_semantics:
            sid = semantic.semantic_id

            if sid in by_id:
                existing = by_id[sid]

                merged = PromotedSemantic(
                    semantic_id=sid,
                    promotion_policy_version=semantic.promotion_policy_version,
                    promotion_step=semantic.promotion_step,
                    promotion_time=semantic.promotion_time,
                    source_candidate_ids=existing.source_candidate_ids + semantic.source_candidate_ids,
                    supporting_episode_ids=list(set(existing.supporting_episode_ids + semantic.supporting_episode_ids)),
                    recurrence_count=existing.recurrence_count + semantic.recurrence_count,
                    persistence_span=max(existing.persistence_span, semantic.persistence_span),
                    stability_classification="stable" if (existing.recurrence_count + semantic.recurrence_count) > 2 else "unstable",
                    confidence_estimate=max(existing.confidence_estimate, semantic.confidence_estimate),
                    tags=semantic.tags or existing.tags,
                    notes=semantic.notes or existing.notes,
                )

                by_id[sid] = merged

            else:
                by_id[sid] = semantic

        return cls(_by_id=by_id)

    def get(self, semantic_id: str) -> PromotedSemantic | None:
        return self._by_id.get(semantic_id)

    def all(self) -> List[PromotedSemantic]:
        return list(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self):
        return iter(self._by_id.values())
