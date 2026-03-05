from __future__ import annotations

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.semantic.registry import SemanticRegistry
from memory.semantic.records import (
    SemanticRecord,
    SemanticProvenance,
    SemanticTemporalScope,
    SemanticStatistics,
    SemanticStability,
)
from memory.semantic_drift.drift_record import DriftRecord
from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.inspection.inspection_builder import InspectionBuilder


def _make_episode_tracker() -> EpisodeTracker:
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace)

    tracker.start_episode(step=0, reason="test")
    tracker.mark_decision(step=5, winner="A")
    tracker.close_episode(step=10, reason="test_end")

    return tracker


def _make_semantic() -> SemanticRecord:
    return SemanticRecord(
        semantic_id="s1",
        policy_version="v0",
        schema_version="v0",
        provenance=SemanticProvenance(
            episode_ids=[1],
            consolidation_ids=None,
            sample_size=1,
        ),
        temporal_scope=SemanticTemporalScope(
            first_observed_step=1,
            last_observed_step=1,
            observation_window=1,
        ),
        pattern_type="pattern",
        pattern_descriptor={"test": True},
        statistics=SemanticStatistics(
            count=1,
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


def _make_drift() -> DriftRecord:
    return DriftRecord(
        semantic_type="pattern",
        window_start_episode=1,
        window_end_episode=1,
        total_occurrences=1,
        unique_episode_count=1,
        first_seen_episode=1,
        last_seen_episode=1,
        persistence_span=0,
        is_novel=True,
        is_recurrent=False,
        is_persistent=False,
        frequency_per_episode=None,
        density=None,
        policy_version="v0",
        schema_version="v0",
        tags={},
    )


def _make_candidate() -> PromotionCandidate:
    return PromotionCandidate(
        semantic_id="s1",
        pattern_type="pattern",
        policy_version="v0",
        schema_version="v0",
        supporting_episode_ids=[1],
        recurrence_count=1,
        persistence_span=0,
        stability_classification="unstable",
        drift_consistent=False,
        disqualified=True,
        disqualification_reasons=["insufficient_recurrence"],
        confidence_estimate=None,
        tags={},
        notes=None,
    )


def test_builder_is_read_only() -> None:
    tracker = _make_episode_tracker()
    semantic = _make_semantic()
    drift = _make_drift()
    candidate = _make_candidate()

    registry = SemanticRegistry.from_records([semantic])

    builder = InspectionBuilder(
        episode_tracker=tracker,
        semantic_registry=registry,
        drift_records=[drift],
        promotion_candidates=[candidate],
    )

    before_episodes = list(tracker.episodes)
    before_semantic = list(registry.records)

    _ = builder.build(report_id="r1")

    after_episodes = list(tracker.episodes)
    after_semantic = list(registry.records)

    assert before_episodes == after_episodes
    assert before_semantic == after_semantic


def test_report_counts_are_correct() -> None:
    tracker = _make_episode_tracker()
    semantic = _make_semantic()
    drift = _make_drift()
    candidate = _make_candidate()

    registry = SemanticRegistry.from_records([semantic])

    builder = InspectionBuilder(
        episode_tracker=tracker,
        semantic_registry=registry,
        drift_records=[drift],
        promotion_candidates=[candidate],
    )

    report = builder.build(report_id="r2")

    assert report.episode_count == 1
    assert report.semantic_record_count == 1
    assert report.drift_record_count == 1
    assert report.promotion_candidate_count == 1


def test_report_is_immutable() -> None:
    tracker = _make_episode_tracker()
    semantic = _make_semantic()

    registry = SemanticRegistry.from_records([semantic])

    builder = InspectionBuilder(
        episode_tracker=tracker,
        semantic_registry=registry,
        drift_records=[],
        promotion_candidates=[],
    )

    report = builder.build(report_id="r3")

    try:
        report.episode_count = 999  # type: ignore[misc]
        mutated = True
    except Exception:
        mutated = False

    assert mutated is False


def test_summaries_are_descriptive_only() -> None:
    tracker = _make_episode_tracker()
    semantic = _make_semantic()
    drift = _make_drift()
    candidate = _make_candidate()

    registry = SemanticRegistry.from_records([semantic])

    builder = InspectionBuilder(
        episode_tracker=tracker,
        semantic_registry=registry,
        drift_records=[drift],
        promotion_candidates=[candidate],
    )

    report = builder.build(report_id="r4")

    assert "episodes_closed" in report.summaries
    assert "semantic_types" in report.summaries
    assert "drift_types" in report.summaries
    assert "promotion_disqualified_count" in report.summaries
