from __future__ import annotations

from learning.diffing.learning_bundle_diff_types import LearningBundleDiff
from learning.inspection.diff_inspection_view import DiffInspectionView


def build_diff_inspection_view(diff: LearningBundleDiff) -> DiffInspectionView:
    semantic = {}
    structural = {}

    if diff.summary:
        semantic_diff = diff.summary.get("semantic")
        structural_diff = diff.summary.get("structural")

        if semantic_diff:
            semantic = {
                "added_terms": semantic_diff.added_terms,
                "removed_terms": semantic_diff.removed_terms,
                "changed_activations": semantic_diff.changed_activations,
            }

        if structural_diff:
            structural = {
                "added_signatures": structural_diff.added_signatures,
                "removed_signatures": structural_diff.removed_signatures,
                "count_deltas": structural_diff.count_deltas,
            }

    return DiffInspectionView(
        has_difference=diff.has_difference,
        semantic=semantic,
        structural=structural,
    )
