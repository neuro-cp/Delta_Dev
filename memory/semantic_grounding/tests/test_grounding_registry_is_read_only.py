from __future__ import annotations

from memory.semantic_grounding.grounding_record import (
    SemanticRegionalGrounding,
)
from memory.semantic_grounding.grounding_registry import (
    SemanticGroundingRegistry,
)


def test_registry_returns_records_without_mutation() -> None:
    record = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pfc"}),
        notes=None,
    )

    registry = SemanticGroundingRegistry([record])

    fetched = registry.get("sem:1")

    assert fetched is record


def test_registry_does_not_modify_records() -> None:
    record = SemanticRegionalGrounding(
        semantic_id="sem:1",
        grounded_regions=frozenset({"pfc"}),
        notes=None,
    )

    registry = SemanticGroundingRegistry([record])

    for r in registry.all():
        assert r.semantic_id == "sem:1"
        assert r.grounded_regions == frozenset({"pfc"})
