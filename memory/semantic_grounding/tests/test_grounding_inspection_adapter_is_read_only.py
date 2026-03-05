from __future__ import annotations

from memory.semantic_grounding.grounding_record import (
    SemanticRegionalGrounding,
)
from memory.semantic_grounding.grounding_registry import (
    SemanticGroundingRegistry,
)
from memory.semantic_grounding.inspection_adapter import (
    SemanticGroundingInspectionAdapter,
)


def test_inspection_adapter_produces_views_only() -> None:
    record = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pfc", "pulvinar"}),
        notes="test",
    )

    registry = SemanticGroundingRegistry([record])
    adapter = SemanticGroundingInspectionAdapter()

    views = adapter.build_views(grounding_registry=registry)

    assert "sem:1" in views
    view = views["sem:1"]

    assert view.semantic_id == "sem:1"
    assert sorted(view.grounded_regions) == ["pfc", "pulvinar"]
    assert view.notes == "test"
