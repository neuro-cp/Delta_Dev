from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregator import aggregate_learning_bundle_diffs
from learning.diffing.learning_bundle_diff_types import LearningBundleDiff


def test_learning_bundle_diff_aggregation_is_deterministic():
    diffs = [
        LearningBundleDiff(
            has_difference=True,
            summary={
                "semantic": type("S", (), {"added_terms": ("a",), "removed_terms": (), "changed_activations": {}})(),
                "structural": type("P", (), {"added_signatures": (), "removed_signatures": (), "count_deltas": {}})(),
            },
        )
    ]

    agg1 = aggregate_learning_bundle_diffs(diffs)
    agg2 = aggregate_learning_bundle_diffs(diffs)

    assert agg1 == agg2
