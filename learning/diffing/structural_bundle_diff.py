from __future__ import annotations

from typing import Dict, Tuple

from learning.inputs.learning_input_bundle import LearningInputBundle
from learning.diffing.learning_bundle_diff_types import StructuralPatternDiff


def diff_structural_patterns(
    a: LearningInputBundle,
    b: LearningInputBundle,
) -> StructuralPatternDiff:
    a_patterns = dict(a.pattern_counts)
    b_patterns = dict(b.pattern_counts)

    a_keys = set(a_patterns.keys())
    b_keys = set(b_patterns.keys())

    added = tuple(sorted(b_keys - a_keys))
    removed = tuple(sorted(a_keys - b_keys))

    deltas: Dict[Tuple, int] = {}
    for key in a_keys & b_keys:
        delta = b_patterns[key] - a_patterns[key]
        if delta != 0:
            deltas[key] = delta

    return StructuralPatternDiff(
        added_signatures=added,
        removed_signatures=removed,
        count_deltas=deltas,
    )
