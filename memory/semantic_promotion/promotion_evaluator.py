from __future__ import annotations

from typing import List

from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord
from memory.semantic_promotion.promotion_candidate import PromotionCandidate


class PromotionEvaluator:
    """
    Offline evaluator for semantic promotion eligibility.

    This evaluator:
    - consumes SemanticRecords and DriftRecords
    - applies a declared promotion policy
    - produces PromotionCandidate artifacts
    - carries NO authority
    - performs NO mutation
    - does NOT promote anything

    Removing this class must not change system behavior.
    """

    def __init__(
        self,
        *,
        policy_version: str = "v0",
        schema_version: str = "v0",
    ) -> None:
        self._policy_version = policy_version
        self._schema_version = schema_version

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def evaluate(
        self,
        *,
        registry: SemanticRegistry,
        drift_records: List[DriftRecord],
    ) -> List[PromotionCandidate]:
        """
        Evaluate semantic patterns for promotion eligibility.

        Returns PromotionCandidates only.
        """
        candidates: List[PromotionCandidate] = []

        drift_by_type = {d.semantic_type: d for d in drift_records}

        for record in registry.records:
            drift = drift_by_type.get(record.pattern_type)

            candidate = self._evaluate_record(
                semantic_id=record.semantic_id,
                pattern_type=record.pattern_type,
                episode_ids=record.provenance.episode_ids,
                drift=drift,
            )

            candidates.append(candidate)

        return candidates

    # --------------------------------------------------
    # Internal evaluation logic
    # --------------------------------------------------

    def _evaluate_record(
        self,
        *,
        semantic_id: str,
        pattern_type: str,
        episode_ids: List[int],
        drift: DriftRecord | None,
    ) -> PromotionCandidate:
        reasons: List[str] = []

        recurrence_count = len(set(episode_ids))
        persistence_span = (
            drift.persistence_span if drift is not None else 0
        )

        # ---- Disqualification rules (policy v0) ----

        if recurrence_count < 2:
            reasons.append("insufficient_recurrence")

        if drift is None:
            reasons.append("no_drift_evidence")

        if drift is not None and not drift.is_persistent:
            reasons.append("insufficient_persistence")

        disqualified = len(reasons) > 0

        return PromotionCandidate(
            semantic_id=semantic_id,
            pattern_type=pattern_type,
            policy_version=self._policy_version,
            schema_version=self._schema_version,
            supporting_episode_ids=list(sorted(set(episode_ids))),
            recurrence_count=recurrence_count,
            persistence_span=persistence_span,
            stability_classification=(
                "stable" if drift and drift.is_persistent else "unstable"
            ),
            drift_consistent=bool(drift and drift.is_recurrent),
            disqualified=disqualified,
            disqualification_reasons=reasons,
            confidence_estimate=None,
            tags={},
            notes=None,
        )
