
from __future__ import annotations

from typing import Iterable, List, Optional, Dict

from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.semantic_promotion.promoted_semantic import PromotedSemantic


class PromotionExecutionAdapter:

    def execute(
        self,
        *,
        candidates: Iterable[PromotionCandidate],
        promotion_step: Optional[int],
        promotion_time: Optional[float],
    ) -> List[PromotedSemantic]:

        merged: Dict[str, PromotedSemantic] = {}

        for candidate in candidates:

            if candidate.disqualified:
                continue

            sid = candidate.semantic_id

            new_sem = PromotedSemantic(
                semantic_id=sid,
                promotion_policy_version=candidate.policy_version,
                promotion_step=promotion_step,
                promotion_time=promotion_time,
                source_candidate_ids=[candidate.semantic_id],
                supporting_episode_ids=candidate.supporting_episode_ids,
                recurrence_count=candidate.recurrence_count,
                persistence_span=candidate.persistence_span,
                stability_classification=candidate.stability_classification,
                confidence_estimate=candidate.confidence_estimate,
                tags=dict(candidate.tags) if candidate.tags else None,
                notes=candidate.notes,
            )

            if sid in merged:
                existing = merged[sid]

                merged[sid] = PromotedSemantic(
                    semantic_id=sid,
                    promotion_policy_version=new_sem.promotion_policy_version,
                    promotion_step=new_sem.promotion_step,
                    promotion_time=new_sem.promotion_time,
                    source_candidate_ids=existing.source_candidate_ids + new_sem.source_candidate_ids,
                    supporting_episode_ids=list(set(existing.supporting_episode_ids + new_sem.supporting_episode_ids)),
                    recurrence_count=existing.recurrence_count + new_sem.recurrence_count,
                    persistence_span=max(existing.persistence_span, new_sem.persistence_span),
                    stability_classification="stable" if (existing.recurrence_count + new_sem.recurrence_count) > 2 else "unstable",
                    confidence_estimate=max(existing.confidence_estimate, new_sem.confidence_estimate),
                    tags=new_sem.tags or existing.tags,
                    notes=new_sem.notes or existing.notes,
                )
            else:
                merged[sid] = new_sem

        return list(merged.values())
