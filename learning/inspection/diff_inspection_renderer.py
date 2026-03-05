from __future__ import annotations

from typing import Any, Dict

from learning.inspection.diff_inspection_view import DiffInspectionView


def render_diff_inspection(view: DiffInspectionView) -> Dict[str, Any]:
    return {
        "has_difference": view.has_difference,
        "semantic": dict(view.semantic),
        "structural": dict(view.structural),
    }
