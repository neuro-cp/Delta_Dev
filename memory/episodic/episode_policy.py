from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EpisodeBoundarySignal:
    """
    Pure advisory signal emitted by the episode policy.

    This object does NOT cause anything to happen.
    It is consumed by higher-level orchestration code.
    """

    start_new: bool = False
    close_active: bool = False
    reason: Optional[str] = None


class EpisodePolicy:
    """
    Episodic boundary policy.

    Responsibilities:
    - Observe runtime events
    - Decide whether an episode boundary is warranted
    - Emit advisory boundary signals

    Non-responsibilities:
    - No state mutation
    - No memory reset
    - No decision authority
    - No executive interpretation
    """

    def __init__(
        self,
        *,
        max_steps_without_decision: int = 500,
        allow_decisionless_episodes: bool = True,
    ) -> None:
        self.max_steps_without_decision = max_steps_without_decision
        self.allow_decisionless_episodes = allow_decisionless_episodes

    # --------------------------------------------------
    # Policy evaluation
    # --------------------------------------------------

    def evaluate(
        self,
        *,
        step: int,
        active_episode_start_step: Optional[int],
        decision_event: bool,
        context_shift: bool = False,
    ) -> Optional[EpisodeBoundarySignal]:
        """
        Evaluate whether an episode boundary should be suggested.

        Inputs are read-only event summaries.
        """

        # --------------------------------------------------
        # No active episode → suggest starting one
        # --------------------------------------------------
        if active_episode_start_step is None:
            return EpisodeBoundarySignal(
                start_new=True,
                reason="no_active_episode",
            )

        # --------------------------------------------------
        # Decision event → suggest closing episode
        # --------------------------------------------------
        if decision_event:
            return EpisodeBoundarySignal(
                close_active=True,
                reason="decision_event",
            )

        # --------------------------------------------------
        # Context shift → force boundary
        # --------------------------------------------------
        if context_shift:
            return EpisodeBoundarySignal(
                close_active=True,
                start_new=True,
                reason="context_shift",
            )

        # --------------------------------------------------
        # Timeout-based closure
        # --------------------------------------------------
        if (
            self.allow_decisionless_episodes
            and (step - active_episode_start_step) >= self.max_steps_without_decision
        ):
            return EpisodeBoundarySignal(
                close_active=True,
                start_new=True,
                reason="episode_timeout",
            )

        # --------------------------------------------------
        # No boundary suggested
        # --------------------------------------------------
        return None
