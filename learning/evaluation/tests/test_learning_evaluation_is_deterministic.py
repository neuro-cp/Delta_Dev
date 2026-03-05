from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate
from learning.evaluation.learning_evaluation_runner import run_learning_evaluation


def test_learning_evaluation_is_deterministic():
    agg = LearningBundleDiffAggregate(
        total_diffs=2,
        semantic_term_add_counts={},
        semantic_term_remove_counts={},
        structural_signature_add_counts={},
        structural_signature_remove_counts={},
    )

    r1 = run_learning_evaluation(agg)
    r2 = run_learning_evaluation(agg)

    assert r1 == r2
