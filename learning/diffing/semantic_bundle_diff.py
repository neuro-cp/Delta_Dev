from __future__ import annotations

from typing import Dict, Tuple

from learning.inputs.learning_input_bundle import LearningInputBundle
from learning.diffing.learning_bundle_diff_types import SemanticDiff


def diff_semantics(
    a: LearningInputBundle,
    b: LearningInputBundle,
) -> SemanticDiff:
    a_terms = a.semantic_ids
    b_terms = b.semantic_ids

    added = tuple(sorted(set(b_terms) - set(a_terms)))
    removed = tuple(sorted(set(a_terms) - set(b_terms)))

    a_latest: Dict[str, float] = {}
    for _, items in a.semantic_activation_snapshots:
        for term, val in items:
            a_latest[term] = val

    b_latest: Dict[str, float] = {}
    for _, items in b.semantic_activation_snapshots:
        for term, val in items:
            b_latest[term] = val

    changed: Dict[str, Tuple[float, float]] = {}
    for term in set(a_latest.keys()) & set(b_latest.keys()):
        if a_latest[term] != b_latest[term]:
            changed[term] = (a_latest[term], b_latest[term])

    return SemanticDiff(
        added_terms=added,
        removed_terms=removed,
        changed_activations=changed,
    )
