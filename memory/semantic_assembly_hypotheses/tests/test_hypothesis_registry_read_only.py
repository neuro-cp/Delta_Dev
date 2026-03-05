from __future__ import annotations

from memory.semantic_assembly_hypotheses.hypothesis_record import (
    SemanticAssemblyHypothesis,
)
from memory.semantic_assembly_hypotheses.hypothesis_registry import (
    SemanticAssemblyHypothesisRegistry,
)


def test_registry_is_read_only_and_symbolic() -> None:
    h = SemanticAssemblyHypothesis(
        semantic_id="sem:test",
        region_id="pfc",
        assembly_ids=frozenset({"A1", "A2"}),
        rationale=None,
    )

    registry = SemanticAssemblyHypothesisRegistry([h])

    fetched = list(registry.for_semantic("sem:test"))

    assert len(fetched) == 1
    assert fetched[0] is h
    assert fetched[0].assembly_ids == frozenset({"A1", "A2"})


def test_registry_permits_multiple_hypotheses_per_semantic() -> None:
    h1 = SemanticAssemblyHypothesis(
        semantic_id="sem:test",
        region_id="pfc",
        assembly_ids=frozenset({"A1"}),
        rationale=None,
    )
    h2 = SemanticAssemblyHypothesis(
        semantic_id="sem:test",
        region_id="association_cortex",
        assembly_ids=frozenset({"B1"}),
        rationale=None,
    )

    registry = SemanticAssemblyHypothesisRegistry([h1, h2])

    results = registry.for_semantic("sem:test")

    assert len(results) == 2
