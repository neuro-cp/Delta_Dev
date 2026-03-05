from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregator import aggregate_learning_bundle_diffs
from learning.diffing.learning_bundle_diff_types import LearningBundleDiff


def test_learning_bundle_diff_aggregation_is_read_only():
    diff = LearningBundleDiff(has_difference=False, summary=None)
    _ = aggregate_learning_bundle_diffs([diff])

    assert diff.summary is None
