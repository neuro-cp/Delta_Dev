from __future__ import annotations

from memory.semantic.registry import SemanticRegistry
from memory.semantic.records import (
    SemanticRecord,
    SemanticProvenance,
    SemanticTemporalScope,
    SemanticStatistics,
    SemanticStability,
)
from memory.semantic_drift.drift_record import DriftRecord
from memory.semantic_promotion.promotion_evaluator import PromotionEvaluator


def _make_semantic(
    *,
    semantic_id: str,
    pattern_type: str,
    episode_ids: list[int],
) -> SemanticRecord:
    first = min(episode_ids)
    last = max(episode_ids)

    return SemanticRecord(
        semantic_id=semantic_id,
        policy_version="v0",
        schema_version="v0",
        provenance=SemanticProvenance(
            episode_ids=episode_ids,
            consolidation_ids=None,
            sample_size=len(episode_ids),
        ),
        temporal_scope=SemanticTemporalScope(
            first_observed_step=first,
            last_observed_step=last,
            observation_window=last - first + 1,
        ),
        pattern_type=pattern_type,
        pattern_descriptor={"test": True},
        statistics=SemanticStatistics(
            count=len(episode_ids),
            frequency=None,
        ),
        stability=SemanticStability(
            support=1.0,
            variance=None,
            decay_rate=None,
        ),
        tags={},
        notes=None,
    )


def _make_drift(
    *,
    semantic_type: str,
    first_seen: int,
    last_seen: int,
    recurrent: bool,
    persistent: bool,
) -> DriftRecord:
    return DriftRecord(
        semantic_type=semantic_type,
        window_start_episode=first_seen,
        window_end_episode=last_seen,
        total_occurrences=last_seen - first_seen + 1,
        unique_episode_count=(
            last_seen - first_seen + 1 if recurrent else 1
        ),
        first_seen_episode=first_seen,
        last_seen_episode=last_seen,
        persistence_span=last_seen - first_seen,
        is_novel=False,
        is_recurrent=recurrent,
        is_persistent=persistent,
        frequency_per_episode=None,
        density=None,
        policy_version="v0",
        schema_version="v0",
        tags={},
    )


def test_promotion_is_offline_and_read_only() -> None:
    record = _make_semantic(
        semantic_id="s1",
        pattern_type="motif",
        episode_ids=[1, 3, 5],
    )

    registry = SemanticRegistry.from_records([record])
    drift = [
        _make_drift(
            semantic_type="motif",
            first_seen=1,
            last_seen=5,
            recurrent=True,
            persistent=True,
        )
    ]

    evaluator = PromotionEvaluator()

    before = registry.records
    _ = evaluator.evaluate(registry=registry, drift_records=drift)
    after = registry.records

    assert before == after


def test_candidate_is_explicitly_disqualified_without_drift() -> None:
    record = _make_semantic(
        semantic_id="s2",
        pattern_type="pattern",
        episode_ids=[2, 4],
    )

    registry = SemanticRegistry.from_records([record])
    evaluator = PromotionEvaluator()

    candidates = evaluator.evaluate(
        registry=registry,
        drift_records=[],
    )

    assert len(candidates) == 1
    cand = candidates[0]

    assert cand.disqualified is True
    assert "no_drift_evidence" in cand.disqualification_reasons


def test_insufficient_recurrence_is_disqualifying() -> None:
    record = _make_semantic(
        semantic_id="s3",
        pattern_type="singleton",
        episode_ids=[7],
    )

    registry = SemanticRegistry.from_records([record])
    drift = [
        _make_drift(
            semantic_type="singleton",
            first_seen=7,
            last_seen=7,
            recurrent=False,
            persistent=False,
        )
    ]

    evaluator = PromotionEvaluator()
    candidates = evaluator.evaluate(
        registry=registry,
        drift_records=drift,
    )

    cand = candidates[0]

    assert cand.disqualified is True
    assert "insufficient_recurrence" in cand.disqualification_reasons


def test_stable_recurrent_pattern_is_not_disqualified() -> None:
    record = _make_semantic(
        semantic_id="s4",
        pattern_type="stable_pattern",
        episode_ids=[1, 4, 7],
    )

    registry = SemanticRegistry.from_records([record])
    drift = [
        _make_drift(
            semantic_type="stable_pattern",
            first_seen=1,
            last_seen=7,
            recurrent=True,
            persistent=True,
        )
    ]

    evaluator = PromotionEvaluator()
    candidates = evaluator.evaluate(
        registry=registry,
        drift_records=drift,
    )

    cand = candidates[0]

    assert cand.disqualified is False
    assert cand.stability_classification == "stable"
    assert cand.recurrence_count == 3
