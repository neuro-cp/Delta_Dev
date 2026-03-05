from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EpisodeBoundaryPolicy:
    """
    Declarative, read-only policy for identifying episodic boundaries.

    This policy:
    - observes runtime snapshots
    - evaluates boundary predicates
    - declares whether a boundary condition is met

    This policy does NOT:
    - open or close episodes
    - mutate state
    - store history
    - assert authority

    Episode lifecycle remains solely owned by EpisodeTracker.
    """

    # --------------------------------------------------
    # Boundary configuration (pure observation)
    # --------------------------------------------------
    close_on_decision: bool = True
    close_on_working_release: bool = False
    max_episode_steps: Optional[int] = None

    # --------------------------------------------------
    # Boundary predicate
    # --------------------------------------------------
    def should_close_episode(
        self,
        *,
        episode_start_step: int,
        current_step: int,
        decision_event: bool,
        working_state_active: Optional[bool] = None,
    ) -> bool:
        """
        Declare whether the *current* episode should terminate.

        All inputs are instantaneous snapshots.
        No internal state is read or written.
        """

        # Decision boundary
        if self.close_on_decision and decision_event:
            return True

        # Working-state release boundary
        if (
            self.close_on_working_release
            and working_state_active is False
        ):
            return True

        # Fixed-duration boundary
        if self.max_episode_steps is not None:
            if (current_step - episode_start_step) >= self.max_episode_steps:
                return True

        return False
