from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate
from learning.evaluation.learning_evaluation_runner import run_learning_evaluation


def test_learning_evaluation_allows_duplicate_semantics():
    agg = LearningBundleDiffAggregate(
        total_diffs=1,
        semantic_term_add_counts={"sem:a": 3},
        semantic_term_remove_counts={},
        structural_signature_add_counts={},
        structural_signature_remove_counts={},
    )

    result = run_learning_evaluation(agg)

    assert result.allowed is True
