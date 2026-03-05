from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate
from learning.inspection.diff_aggregate_inspection_view import DiffAggregateInspectionView


def build_diff_aggregate_inspection_view(
    aggregate: LearningBundleDiffAggregate,
) -> DiffAggregateInspectionView:
    return DiffAggregateInspectionView(
        total_diffs=aggregate.total_diffs,
        semantic_term_add_counts=dict(aggregate.semantic_term_add_counts),
        semantic_term_remove_counts=dict(aggregate.semantic_term_remove_counts),
        structural_signature_add_counts=dict(aggregate.structural_signature_add_counts),
        structural_signature_remove_counts=dict(aggregate.structural_signature_remove_counts),
    )
