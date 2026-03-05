from __future__ import annotations

from typing import Any, Dict

from learning.inspection.diff_aggregate_inspection_view import DiffAggregateInspectionView


def render_diff_aggregate_inspection(
    view: DiffAggregateInspectionView,
) -> Dict[str, Any]:
    return {
        "total_diffs": view.total_diffs,
        "semantic": {
            "added": dict(view.semantic_term_add_counts),
            "removed": dict(view.semantic_term_remove_counts),
        },
        "structural": {
            "added": dict(view.structural_signature_add_counts),
            "removed": dict(view.structural_signature_remove_counts),
        },
    }
