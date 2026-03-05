from __future__ import annotations

from memory.semantic.registry import SemanticRegistry
from memory.semantic.records import (
    SemanticRecord,
    SemanticProvenance,
    SemanticTemporalScope,
    SemanticStatistics,
    SemanticStability,
)
from memory.semantic_drift.drift_analyzer import DriftAnalyzer


def _make_semantic(
    *,
    semantic_id: str,
    pattern_type: str,
    episode_ids: list[int],
) -> SemanticRecord:
    first_ep = min(episode_ids)
    last_ep = max(episode_ids)

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
            first_observed_step=first_ep,
            last_observed_step=last_ep,
            observation_window=last_ep - first_ep + 1,
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


def test_drift_is_offline_and_read_only() -> None:
    records = [
        _make_semantic(semantic_id="s1", pattern_type="freq", episode_ids=[1]),
        _make_semantic(semantic_id="s2", pattern_type="freq", episode_ids=[2]),
    ]

    registry = SemanticRegistry.from_records(records)
    analyzer = DriftAnalyzer(registry)

    before = registry.records

    _ = analyzer.analyze(
        window_start_episode=1,
        window_end_episode=3,
    )

    after = registry.records
    assert before == after


def test_drift_detects_novelty_relative_to_window() -> None:
    records = [
        _make_semantic(semantic_id="s1", pattern_type="pattern", episode_ids=[1]),
        _make_semantic(semantic_id="s2", pattern_type="pattern", episode_ids=[3]),
    ]

    registry = SemanticRegistry.from_records(records)
    analyzer = DriftAnalyzer(registry)

    drift = analyzer.analyze(
        window_start_episode=2,
        window_end_episode=4,
    )

    assert len(drift) == 1
    rec = drift[0]

    assert rec.is_novel is True
    assert rec.first_seen_episode == 3


def test_drift_detects_recurrence_and_persistence() -> None:
    records = [
        _make_semantic(semantic_id="s1", pattern_type="motif", episode_ids=[1]),
        _make_semantic(semantic_id="s2", pattern_type="motif", episode_ids=[3]),
        _make_semantic(semantic_id="s3", pattern_type="motif", episode_ids=[5]),
    ]

    registry = SemanticRegistry.from_records(records)
    analyzer = DriftAnalyzer(registry)

    drift = analyzer.analyze(
        window_start_episode=1,
        window_end_episode=6,
    )

    rec = drift[0]

    assert rec.is_recurrent is True
    assert rec.is_persistent is True
    assert rec.persistence_span == 4
    assert rec.unique_episode_count == 3


def test_drift_is_grouped_by_semantic_type() -> None:
    records = [
        _make_semantic(semantic_id="a", pattern_type="A", episode_ids=[1]),
        _make_semantic(semantic_id="b", pattern_type="B", episode_ids=[1]),
        _make_semantic(semantic_id="c", pattern_type="A", episode_ids=[2]),
    ]

    registry = SemanticRegistry.from_records(records)
    analyzer = DriftAnalyzer(registry)

    drift = analyzer.analyze(
        window_start_episode=1,
        window_end_episode=3,
    )

    types = {d.semantic_type for d in drift}
    assert types == {"A", "B"}
