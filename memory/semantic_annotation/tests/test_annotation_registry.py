from __future__ import annotations

from memory.semantic_annotation.annotation_registry import AnnotationRegistry
from memory.semantic_annotation.annotation_record import SemanticAnnotationRecord


def _make_annotation(
    *,
    annotation_id: str,
    episode_id: int,
    annotation_type: str,
) -> SemanticAnnotationRecord:
    return SemanticAnnotationRecord(
        annotation_id=annotation_id,
        episode_id=episode_id,
        annotation_type=annotation_type,
        source_semantic_ids=[],
        policy_version="v0",
        schema_version="v0",
        applied_during_replay=True,
        episode_closed=True,
        descriptor="test annotation",
        metrics={},
        confidence=None,
        tags={},
        notes=None,
    )


def test_registry_is_read_only() -> None:
    records = [
        _make_annotation(
            annotation_id="a1",
            episode_id=1,
            annotation_type="semantic_pattern_match",
        )
    ]

    registry = AnnotationRegistry.from_records(records)

    before = registry.records
    before.append("corruption")

    after = registry.records

    assert len(after) == 1


def test_lookup_by_episode() -> None:
    records = [
        _make_annotation(
            annotation_id="a1",
            episode_id=1,
            annotation_type="semantic_pattern_match",
        ),
        _make_annotation(
            annotation_id="a2",
            episode_id=2,
            annotation_type="semantic_pattern_match",
        ),
    ]

    registry = AnnotationRegistry.from_records(records)

    ep1 = registry.by_episode(1)

    assert len(ep1) == 1
    assert ep1[0].episode_id == 1


def test_lookup_by_type() -> None:
    records = [
        _make_annotation(
            annotation_id="a1",
            episode_id=1,
            annotation_type="semantic_pattern_match",
        ),
        _make_annotation(
            annotation_id="a2",
            episode_id=2,
            annotation_type="temporal_pattern",
        ),
    ]

    registry = AnnotationRegistry.from_records(records)

    matches = registry.by_type("semantic_pattern_match")

    assert len(matches) == 1
    assert matches[0].annotation_type == "semantic_pattern_match"


def test_summary_counts() -> None:
    records = [
        _make_annotation(
            annotation_id="a1",
            episode_id=1,
            annotation_type="semantic_pattern_match",
        ),
        _make_annotation(
            annotation_id="a2",
            episode_id=2,
            annotation_type="semantic_pattern_match",
        ),
        _make_annotation(
            annotation_id="a3",
            episode_id=3,
            annotation_type="temporal_pattern",
        ),
    ]

    registry = AnnotationRegistry.from_records(records)

    summary = registry.summary()

    assert summary["semantic_pattern_match"] == 2
    assert summary["temporal_pattern"] == 1
