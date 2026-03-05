from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from learning.diffing.learning_bundle_diff_types import LearningBundleDiff
from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate


def aggregate_learning_bundle_diffs(
    diffs: Iterable[LearningBundleDiff],
) -> LearningBundleDiffAggregate:
    semantic_add = defaultdict(int)
    semantic_remove = defaultdict(int)
    structural_add = defaultdict(int)
    structural_remove = defaultdict(int)

    total = 0

    for diff in diffs:
        total += 1
        if not diff.summary:
            continue

        sem = diff.summary.get("semantic")
        if sem:
            for t in sem.added_terms:
                semantic_add[t] += 1
            for t in sem.removed_terms:
                semantic_remove[t] += 1

        struct = diff.summary.get("structural")
        if struct:
            for s in struct.added_signatures:
                structural_add[s] += 1
            for s in struct.removed_signatures:
                structural_remove[s] += 1

    return LearningBundleDiffAggregate(
        total_diffs=total,
        semantic_term_add_counts=dict(semantic_add),
        semantic_term_remove_counts=dict(semantic_remove),
        structural_signature_add_counts=dict(structural_add),
        structural_signature_remove_counts=dict(structural_remove),
    )
