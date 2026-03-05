from __future__ import annotations

import pytest

from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate
from learning.evaluation.learning_evaluation_runner import run_learning_evaluation


def test_learning_evaluation_hard_failure():
    agg = LearningBundleDiffAggregate(
        total_diffs=-1,
        semantic_term_add_counts={},
        semantic_term_remove_counts={},
        structural_signature_add_counts={},
        structural_signature_remove_counts={},
    )

    with pytest.raises(AssertionError):
        assert agg.total_diffs >= 0
        run_learning_evaluation(agg)
