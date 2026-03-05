from __future__ import annotations

from typing import Iterable, Optional, Dict

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame
from memory.semantic_activation.semantic_activation_record import (
    SemanticActivationRecord,
)


class SemanticActivationObserver:
    """
    Offline adapter that attaches semantic activation data
    to ObservationFrame objects.

    CONTRACT:
    - Offline only
    - Read-only
    - No hypothesis access
    - No interpretation
    - Removal invariant holds
    """

    def attach(
        self,
        *,
        frame: ObservationFrame,
        activation: Optional[SemanticActivationRecord],
    ) -> ObservationFrame:
        """
        Return a new ObservationFrame with semantic activation attached.

        If activation is None, the frame is returned unchanged.
        """

        if activation is None:
            return frame

        # NOTE:
        # We construct a NEW ObservationFrame to preserve immutability.
        # No mutation, no side effects.
        return ObservationFrame(
            step=frame.step,
            salience=frame.salience,
            assembly_outputs=frame.assembly_outputs,
            semantic_activation=dict(activation.activations),
        )

    def attach_many(
        self,
        *,
        frames: Iterable[ObservationFrame],
        activations: Dict[int, SemanticActivationRecord],
    ) -> Iterable[ObservationFrame]:
        """
        Attach semantic activation snapshots to frames by step index.

        frames: iterable of ObservationFrame
        activations: mapping step -> SemanticActivationRecord
        """

        for frame in frames:
            yield self.attach(
                frame=frame,
                activation=activations.get(frame.step),
            )
