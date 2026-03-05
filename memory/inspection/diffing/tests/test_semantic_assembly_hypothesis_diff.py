from __future__ import annotations

from memory.semantic_assembly_hypotheses.inspection_adapter import (
    SemanticAssemblyHypothesisView,
)
from memory.inspection.diffing.semantic_assembly_hypothesis_diff import (
    diff_semantic_assembly_hypotheses,
)


def test_hypothesis_diff_detects_additions_and_removals() -> None:
    before = {
        "sem:a": [
            SemanticAssemblyHypothesisView(
                semantic_id="sem:a",
                region_id="pfc",
                assembly_ids=["A1"],
                rationale=None,
            )
        ]
    }

    after = {
        "sem:a": [
            SemanticAssemblyHypothesisView(
                semantic_id="sem:a",
                region_id="pfc",
                assembly_ids=["A1", "A2"],
                rationale=None,
            )
        ]
    }

    diff = diff_semantic_assembly_hypotheses(before=before, after=after)

    assert ("sem:a", "pfc", ("A1", "A2")) in diff["sem:a"]["added_hypotheses"]
    assert ("sem:a", "pfc", ("A1",)) in diff["sem:a"]["removed_hypotheses"]
