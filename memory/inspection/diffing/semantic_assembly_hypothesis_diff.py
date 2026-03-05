from __future__ import annotations

from typing import Dict, List, Set, Tuple

from memory.semantic_assembly_hypotheses.inspection_adapter import (
    SemanticAssemblyHypothesisView,
)


def _view_key(view: SemanticAssemblyHypothesisView) -> Tuple[str, str, Tuple[str, ...]]:
    return (
        view.semantic_id,
        view.region_id,
        tuple(view.assembly_ids),
    )


def diff_semantic_assembly_hypotheses(
    *,
    before: Dict[str, List[SemanticAssemblyHypothesisView]],
    after: Dict[str, List[SemanticAssemblyHypothesisView]],
) -> Dict[str, Dict[str, Set[Tuple[str, str, Tuple[str, ...]]]]]:
    """
    Diff semantic → assembly hypotheses.

    Reports added / removed hypotheses per semantic.
    """

    diff: Dict[str, Dict[str, Set[Tuple[str, str, Tuple[str, ...]]]]] = {}

    all_semantics = set(before.keys()) | set(after.keys())

    for semantic_id in all_semantics:
        before_set = {
            _view_key(v)
            for v in before.get(semantic_id, [])
        }
        after_set = {
            _view_key(v)
            for v in after.get(semantic_id, [])
        }

        added = after_set - before_set
        removed = before_set - after_set

        if added or removed:
            diff[semantic_id] = {
                "added_hypotheses": added,
                "removed_hypotheses": removed,
            }

    return diff
