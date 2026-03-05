# learning/adapters/learning_to_promotion_adapter.py

from __future__ import annotations

from typing import Dict, List

from memory.semantic_promotion.promotion_candidate import PromotionCandidate


class LearningToPromotionAdapter:
    """
    Pure offline adapter.

    Transforms an approved GovernanceRecord into
    PromotionCandidate artifacts.

    CONTRACT:
    - Pure
    - Deterministic
    - No mutation
    - No registry access
    - No runtime imports
    - No authority
    """

    POLICY_VERSION = "v0"
    SCHEMA_VERSION = "s1"

    def build_candidates(
        self,
        *,
        governance_record: Dict,
    ) -> List[PromotionCandidate]:
        """
        Extract promotable deltas from governance_record.

        Expected governance_record structure:
            {
                "approved": bool,
                "applied_deltas": [
                    {
                        "semantic_id": str,
                        "pattern_type": str,
                        "supporting_episode_ids": List[int],
                        "recurrence_count": int,
                        "persistence_span": int,
                        "stability_classification": str,
                    }
                ]
            }

        If governance_record["approved"] is False,
        returns empty list.
        """

        if not governance_record.get("approved", False):
            return []

        deltas = governance_record.get("applied_deltas", [])
        candidates: List[PromotionCandidate] = []

        for delta in deltas:
            candidates.append(
                PromotionCandidate(
                    semantic_id=delta["semantic_id"],
                    pattern_type=delta["pattern_type"],
                    policy_version=self.POLICY_VERSION,
                    schema_version=self.SCHEMA_VERSION,
                    supporting_episode_ids=list(
                        sorted(set(delta["supporting_episode_ids"]))
                    ),
                    recurrence_count=delta["recurrence_count"],
                    persistence_span=delta["persistence_span"],
                    stability_classification=delta[
                        "stability_classification"
                    ],
                    drift_consistent=True,
                    disqualified=False,
                    confidence_estimate=None,
                    tags={},
                    notes="derived_from_governance_record",
                )
            )

        return candidates