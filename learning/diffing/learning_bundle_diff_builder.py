from __future__ import annotations

from learning.inputs.learning_input_bundle import LearningInputBundle
from learning.diffing.learning_bundle_diff_types import LearningBundleDiff
from learning.diffing.semantic_bundle_diff import diff_semantics
from learning.diffing.structural_bundle_diff import diff_structural_patterns


def build_learning_bundle_diff(
    a: LearningInputBundle,
    b: LearningInputBundle,
) -> LearningBundleDiff:
    semantic_diff = diff_semantics(a, b)
    structural_diff = diff_structural_patterns(a, b)

    has_difference = (
        bool(semantic_diff.added_terms)
        or bool(semantic_diff.removed_terms)
        or bool(semantic_diff.changed_activations)
        or bool(structural_diff.added_signatures)
        or bool(structural_diff.removed_signatures)
        or bool(structural_diff.count_deltas)
    )

    return LearningBundleDiff(
        has_difference=has_difference,
        summary={
            "semantic": semantic_diff,
            "structural": structural_diff,
        },
    )
