from __future__ import annotations

from memory.semantic_grounding.grounding_registry import (
    SemanticGroundingRegistry,
)
from memory.semantic_grounding.grounding_record import (
    SemanticRegionalGrounding,
)


def test_registry_does_not_merge_or_infer() -> None:
    r1 = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pfc"}),
        notes=None,
    )
    r2 = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pulvinar"}),
        notes=None,
    )

    registry = SemanticGroundingRegistry([r1, r2])

    # Last-write wins is acceptable; merging is forbidden
    fetched = registry.get("sem:1")

    assert fetched.grounded_regions in (
        frozenset({"pfc"}),
        frozenset({"pulvinar"}),
    )
