from __future__ import annotations

from typing import Dict, Set

from memory.semantic_grounding.inspection_adapter import (
    SemanticRegionalGroundingView,
)


def diff_semantic_grounding(
    *,
    before: Dict[str, SemanticRegionalGroundingView],
    after: Dict[str, SemanticRegionalGroundingView],
) -> Dict[str, Dict[str, Set[str]]]:
    """
    Diff semantic → regional grounding views.

    Returns per-semantic:
    - added_regions
    - removed_regions
    """

    diff: Dict[str, Dict[str, Set[str]]] = {}

    all_semantics = set(before.keys()) | set(after.keys())

    for semantic_id in all_semantics:
        before_regions = (
            set(before[semantic_id].grounded_regions)
            if semantic_id in before
            else set()
        )
        after_regions = (
            set(after[semantic_id].grounded_regions)
            if semantic_id in after
            else set()
        )

        added = after_regions - before_regions
        removed = before_regions - after_regions

        if added or removed:
            diff[semantic_id] = {
                "added_regions": added,
                "removed_regions": removed,
            }

    return diff
