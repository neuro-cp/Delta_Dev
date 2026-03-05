from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from memory.semantic_assembly_hypotheses.hypothesis_registry import (
    SemanticAssemblyHypothesisRegistry,
)
from memory.semantic_assembly_hypotheses.hypothesis_record import (
    SemanticAssemblyHypothesis,
)


@dataclass(frozen=True)
class SemanticAssemblyHypothesisView:
    """
    Inspection-only view of a semantic → assembly hypothesis.
    """

    semantic_id: str
    region_id: str
    assembly_ids: List[str]
    rationale: str | None


class SemanticAssemblyHypothesisInspectionAdapter:
    """
    Read-only adapter exposing semantic → assembly hypotheses
    for inspection only.

    CONTRACT:
    - No mutation
    - No inference
    - No runtime coupling
    """

    def build_views(
        self,
        *,
        registry: SemanticAssemblyHypothesisRegistry,
    ) -> Dict[str, List[SemanticAssemblyHypothesisView]]:
        views: Dict[str, List[SemanticAssemblyHypothesisView]] = {}

        for hypothesis in registry.all():
            view = SemanticAssemblyHypothesisView(
                semantic_id=hypothesis.semantic_id,
                region_id=hypothesis.region_id,
                assembly_ids=sorted(hypothesis.assembly_ids),
                rationale=hypothesis.rationale,
            )

            views.setdefault(hypothesis.semantic_id, []).append(view)

        return views
