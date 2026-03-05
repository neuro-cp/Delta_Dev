from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


@dataclass(frozen=True)
class SemanticActivationInspectionView:
    """
    Human-facing inspection view of semantic activation
    observed during offline cognition.

    Descriptive only.
    No authority.
    """

    step: int
    activations: Dict[str, float]


class SemanticActivationInspectionBuilder:
    """
    Builds inspection-only views of semantic activation
    from ObservationFrames.

    CONTRACT:
    - Pure extraction
    - No aggregation
    - No thresholds
    - No inference
    """

    def build(
        self,
        *,
        frames: List[ObservationFrame],
    ) -> List[SemanticActivationInspectionView]:
        views: List[SemanticActivationInspectionView] = []

        for frame in frames:
            activations = getattr(frame, "semantic_activation", None)
            if not activations:
                continue

            views.append(
                SemanticActivationInspectionView(
                    step=frame.step,
                    activations=dict(activations),
                )
            )

        return views
