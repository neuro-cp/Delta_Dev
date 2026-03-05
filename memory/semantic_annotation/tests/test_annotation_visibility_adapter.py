from __future__ import annotations

import pytest

from memory.semantic_annotation.annotation_visibility_adapter import (
    AnnotationVisibilityAdapter,
    AnnotationVisibilityContext,
)
from memory.semantic_annotation.annotation_registry import AnnotationRegistry
from memory.semantic_annotation.annotation_record import SemanticAnnotationRecord


def _make_annotation(*, episode_id: int) -> SemanticAnnotationRecord:
    return SemanticAnnotationRecord(
        annotation_id="a1",
        episode_id=episode_id,
        annotation_type="semantic_pattern_match",
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


def test_visibility_is_context_gated() -> None:
    registry = AnnotationRegistry.from_records(
        [_make_annotation(episode_id=1)]
    )
    adapter = AnnotationVisibilityAdapter(registry)

    anns = adapter.visible_annotations(
        episode_id=1,
        context=AnnotationVisibilityContext.POST_DECISION,
    )

    assert len(anns) == 1


def test_visibility_rejects_invalid_context() -> None:
    registry = AnnotationRegistry.from_records(
        [_make_annotation(episode_id=1)]
    )
    adapter = AnnotationVisibilityAdapter(registry)

    with pytest.raises(ValueError):
        adapter.visible_annotations(
            episode_id=1,
            context="runtime_step",  # type: ignore[arg-type]
        )


def test_visibility_is_read_only() -> None:
    registry = AnnotationRegistry.from_records(
        [_make_annotation(episode_id=1)]
    )
    adapter = AnnotationVisibilityAdapter(registry)

    before = registry.records
    _ = adapter.visible_annotations(
        episode_id=1,
        context=AnnotationVisibilityContext.POST_DECISION,
    )
    after = registry.records

    assert before == after
