from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate
from learning.inspection.diff_aggregate_inspection_builder import build_diff_aggregate_inspection_view


def test_diff_aggregate_inspection_matches_aggregate():
    agg = LearningBundleDiffAggregate(
        total_diffs=2,
        semantic_term_add_counts={"a": 1},
        semantic_term_remove_counts={"b": 2},
        structural_signature_add_counts={("sig",): 1},
        structural_signature_remove_counts={},
    )

    view = build_diff_aggregate_inspection_view(agg)

    assert view.total_diffs == 2
    assert view.semantic_term_add_counts["a"] == 1
    assert view.semantic_term_remove_counts["b"] == 2
