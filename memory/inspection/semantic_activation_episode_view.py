from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from memory.semantic_activation.inspection.windowed_activation_view import (
    WindowedActivationInspectionView,
)


@dataclass(frozen=True)
class SemanticActivationEpisodeView:
    """
    Episode-scoped inspection view of windowed semantic activation.

    Descriptive only.
    No authority.
    """

    episode_id: int
    scale_name: str
    windowed_activations: List[WindowedActivationInspectionView]


class SemanticActivationEpisodeViewBuilder:
    """
    Builds episode-level inspection views for semantic activation.

    CONTRACT:
    - Presentation only
    - No aggregation
    - No interpretation
    - No thresholds
    """

    def build(
        self,
        *,
        episode_id: int,
        windowed_by_scale: Dict[str, List[WindowedActivationInspectionView]],
    ) -> List[SemanticActivationEpisodeView]:
        views: List[SemanticActivationEpisodeView] = []

        for scale, windowed_views in windowed_by_scale.items():
            views.append(
                SemanticActivationEpisodeView(
                    episode_id=episode_id,
                    scale_name=scale,
                    windowed_activations=list(windowed_views),
                )
            )

        return views
