from __future__ import annotations

from typing import Iterable, List

from .boundary_event import BoundaryEvent
from engine.observation.observation_event import ObservationEvent


class BoundaryAdapter:
    """
    Episodic boundary adapter.

    Responsibilities:
    - Consume observation events (facts)
    - Apply simple, local temporal logic
    - Emit declarative BoundaryEvent objects

    Non-responsibilities:
    - No episode state
    - No tracker access
    - No runtime mutation
    - No learning or thresholds
    """

    def __init__(self) -> None:
        self._stable_count = 0

    def step(
        self,
        *,
        step: int,
        observation_events: Iterable[ObservationEvent],
    ) -> List[BoundaryEvent]:
        events: List[BoundaryEvent] = []

        # --------------------------------------------------
        # Derive a simple "active" fact from observations
        # (this is intentionally conservative)
        # --------------------------------------------------
        active = any(
            getattr(ev, "kind", None) == "state_active"
            for ev in observation_events
        )

        if active:
            self._stable_count += 1
        else:
            self._stable_count = 0

        # --------------------------------------------------
        # Boundary declaration (edge only, no persistence)
        # --------------------------------------------------
        if self._stable_count == 1:
            events.append(
                BoundaryEvent(
                    step=step,
                    reason="state_entered",
                )
            )

        return events