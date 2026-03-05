from __future__ import annotations

from typing import Any, Dict

from learning.diffing.learning_bundle_diff import LearningBundleDiff
from learning.diffing.learning_bundle_diff_types import SemanticDiff, StructuralPatternDiff


def serialize_diff(diff: LearningBundleDiff) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "has_difference": diff.has_difference,
        "semantic": None,
        "structural": None,
    }

    if diff.summary:
        sem: SemanticDiff = diff.summary.get("semantic")
        struct: StructuralPatternDiff = diff.summary.get("structural")

        if sem:
            out["semantic"] = {
                "added_terms": list(sem.added_terms),
                "removed_terms": list(sem.removed_terms),
                "changed_activations": {
                    k: {"before": v[0], "after": v[1]}
                    for k, v in sem.changed_activations.items()
                },
            }

        if struct:
            out["structural"] = {
                "added_signatures": list(struct.added_signatures),
                "removed_signatures": list(struct.removed_signatures),
                "count_deltas": dict(struct.count_deltas),
            }

    return out
