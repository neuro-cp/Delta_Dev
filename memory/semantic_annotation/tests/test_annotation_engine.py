from __future__ import annotations

import copy

from memory.episodic.episode_structure import Episode
from memory.semantic.records import (
    SemanticRecord,
    SemanticProvenance,
    SemanticTemporalScope,
    SemanticStatistics,
    SemanticStability,
)
from memory.semantic.registry import SemanticRegistry
from memory.semantic_annotation.annotation_engine import SemanticAnnotationEngine


def _make_episode(*, episode_id: int, decisions: int) -> Episode:
    ep = Episode(
        episode_id=episode_id,
        start_step=0,
        start_time=0.0,
    )
    for i in range(decisions):
        ep.mark_decision(
            step=i + 1,
            time=(i + 1) * 0.01,
            winner="A",
            confidence=0.9,
        )
    ep.close(step=10, time=0.10)
    return ep


def _make_semantic(i: int) -> SemanticRecord:
    return SemanticRecord(
        semantic_id=f"s{i}",
        policy_version="v0",
        schema_version="v0",
        provenance=SemanticProvenance(
            episode_ids=[i],
            sample_size=1,
        ),
        temporal_scope=SemanticTemporalScope(
            first_observed_step=0,
            last_observed_step=10,
            observation_window=10,
        ),
        pattern_type="frequency",
        pattern_descriptor={"kind": "decision_frequency"},
        statistics=SemanticStatistics(
            count=i + 1,
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


def test_annotation_is_additive_and_offline() -> None:
    episodes = [
        _make_episode(episode_id=1, decisions=2),
        _make_episode(episode_id=2, decisions=0),
    ]

    semantics = [_make_semantic(1)]
    registry = SemanticRegistry.from_records(semantics)

    engine = SemanticAnnotationEngine(
        semantic_registry=registry,
        policy_version="v0",
        schema_version="v0",
    )

    annotations = engine.annotate_episodes(episodes)

    # One annotation per closed episode
    assert len(annotations) == len(episodes)

    for ann in annotations:
        assert ann.applied_during_replay is True
        assert ann.episode_closed is True
        assert ann.annotation_type == "semantic_pattern_match"


def test_episode_objects_are_not_mutated() -> None:
    ep = _make_episode(episode_id=1, decisions=1)
    ep_snapshot = copy.deepcopy(ep)

    registry = SemanticRegistry.from_records([_make_semantic(1)])
    engine = SemanticAnnotationEngine(semantic_registry=registry)

    _ = engine.annotate_episodes([ep])

    # Episode unchanged
    assert ep == ep_snapshot


def test_annotations_are_discardable() -> None:
    episodes = [_make_episode(episode_id=1, decisions=1)]
    registry = SemanticRegistry.from_records([_make_semantic(1)])

    engine = SemanticAnnotationEngine(semantic_registry=registry)

    annotations_first = engine.annotate_episodes(episodes)

    # Discard annotations entirely
    del annotations_first

    # Re-run annotation
    annotations_second = engine.annotate_episodes(episodes)

    # Deterministic descriptors
    assert annotations_second[0].descriptor.startswith("episode resembles")
