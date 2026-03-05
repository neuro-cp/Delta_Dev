from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class WindowedActivationInspectionView:
    """
    Human-facing inspection view of windowed semantic activation.

    Descriptive only.
    No authority.
    """

    window_index: int
    activations: Dict[str, float]


class WindowedActivationInspectionBuilder:
    """
    Builds inspection views from windowed activation snapshots.

    CONTRACT:
    - Presentation only
    - No inference
    - No aggregation
    - No thresholds
    """

    def build(
        self,
        *,
        windowed_history: List[Dict[str, float]],
    ) -> List[WindowedActivationInspectionView]:
        views: List[WindowedActivationInspectionView] = []

        for idx, snapshot in enumerate(windowed_history):
            views.append(
                WindowedActivationInspectionView(
                    window_index=idx,
                    activations=dict(snapshot),
                )
            )

        return views
