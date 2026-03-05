from __future__ import annotations

from memory.semantic_grounding.inspection_adapter import (
    SemanticRegionalGroundingView,
)
from memory.inspection.diffing.semantic_grounding_diff import (
    diff_semantic_grounding,
)


def test_grounding_diff_detects_added_and_removed_regions() -> None:
    before = {
        "sem:a": SemanticRegionalGroundingView(
            semantic_id="sem:a",
            grounded_regions=["pfc"],
            notes=None,
        )
    }

    after = {
        "sem:a": SemanticRegionalGroundingView(
            semantic_id="sem:a",
            grounded_regions=["pfc", "pulvinar"],
            notes=None,
        )
    }

    diff = diff_semantic_grounding(before=before, after=after)

    assert diff["sem:a"]["added_regions"] == {"pulvinar"}
    assert diff["sem:a"]["removed_regions"] == set()
