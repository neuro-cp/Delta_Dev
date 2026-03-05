from __future__ import annotations

from typing import Iterable

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic_boundary.boundary_event import BoundaryEvent


class EpisodeRuntimeHook:
    """
    Runtime-facing episodic hook (read-only bridge).

    Responsibilities:
    - Receive declared episodic boundary events
    - Delegate lifecycle transitions to EpisodeTracker

    Non-responsibilities:
    - No boundary detection
    - No authority
    - No learning
    - No runtime mutation
    """

    def __init__(self, *, tracker: EpisodeTracker) -> None:
        self.tracker = tracker

    def step(
        self,
        *,
        step: int,
        boundary_events: Iterable[BoundaryEvent],
    ) -> None:
        """
        Called once per runtime step.

        Applies boundary events produced by the episodic
        boundary layer.
        """

        # --------------------------------------------------
        # Ensure an episode exists
        # --------------------------------------------------
        if not self.tracker.has_active_episode():
            self.tracker.start_episode(
                step=step,
                reason="initial",
            )

        # --------------------------------------------------
        # Apply boundary events (declarative only)
        # --------------------------------------------------
       
        for event in boundary_events:
            self.tracker.close_episode(
                step=step,
                reason=event.reason,
            )

        # --------------------------------------------------
        # Open next episode if one just closed
        # --------------------------------------------------
        if not self.tracker.has_active_episode():
            self.tracker.start_episode(
                step=step,
                reason="boundary",
            )