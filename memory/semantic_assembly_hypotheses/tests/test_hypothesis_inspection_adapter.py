from __future__ import annotations

from memory.semantic_assembly_hypotheses.hypothesis_record import (
    SemanticAssemblyHypothesis,
)
from memory.semantic_assembly_hypotheses.hypothesis_registry import (
    SemanticAssemblyHypothesisRegistry,
)
from memory.semantic_assembly_hypotheses.inspection_adapter import (
    SemanticAssemblyHypothesisInspectionAdapter,
)


def test_inspection_adapter_builds_views_only() -> None:
    h = SemanticAssemblyHypothesis(
        semantic_id="sem:test",
        region_id="pfc",
        assembly_ids=frozenset({"A2", "A1"}),
        rationale="symbolic",
    )

    registry = SemanticAssemblyHypothesisRegistry([h])
    adapter = SemanticAssemblyHypothesisInspectionAdapter()

    views = adapter.build_views(registry=registry)

    assert "sem:test" in views
    view = views["sem:test"][0]

    assert view.semantic_id == "sem:test"
    assert view.region_id == "pfc"
    assert view.assembly_ids == ["A1", "A2"]
    assert view.rationale == "symbolic"
