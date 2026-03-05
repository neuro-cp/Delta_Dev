from __future__ import annotations

from typing import Optional, List, Dict

from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace


class EpisodeTracker:
    """
    Passive episodic boundary tracker.

    Responsibilities:
    - Create episodes
    - Annotate decisions
    - Close episodes
    - Maintain episode history
    - Emit trace records

    Non-responsibilities:
    - No control
    - No gating
    - No learning
    - No reset authority
    """

    @property
    def episodes(self):
        """
        Read-only access to all episodes in creation order.

        Returned list must not be mutated by callers.
        """
        return list(self._episodes)

    def __init__(self, trace: EpisodeTrace) -> None:
        self._trace = trace
        self._episodes: List[Episode] = []
        self._active: Optional[Episode] = None
        self._next_id: int = 0

    # --------------------------------------------------
    # Episode lifecycle (authoritative, state-only)
    # --------------------------------------------------

    def start_episode(
        self,
        *,
        step: int,
        tags: Optional[Dict] = None,
        reason: str = "explicit_start",
    ) -> Episode:
        """
        Start a new episode.

        If an episode is already active, it is closed implicitly.
        """
        if self._active is not None:
            self.close_episode(step=step, reason="implicit_close")

        episode = Episode(
            episode_id=self._next_id,
            start_step=step,
            start_time=0.0,  # Phase 6+
            tags=tags or {},
        )

        self._trace.record_start(
            episode_id=episode.episode_id,
            step=step,
            reason=reason,
        )

        self._episodes.append(episode)
        self._active = episode
        self._next_id += 1
        return episode

    def mark_decision(
        self,
        *,
        step: int,
        winner: Optional[str] = None,
        confidence: Optional[float] = None,
        payload: Optional[Dict] = None,
    ) -> None:
        """
        Annotate the active episode with a decision.

        If no episode exists, one is created implicitly.
        """
        if self._active is None:
            self.start_episode(
                step=step,
                reason="implicit_decision_episode",
            )

        self._active.mark_decision(
            step=step,
            time=0.0,  # Phase 6+
            winner=winner,
            confidence=confidence,
            payload=payload,
        )

        self._trace.record_decision(
        episode_id=self._active.episode_id,
        step=step,
        winner=winner,
        confidence=confidence,
    )


    def close_episode(
        self,
        *,
        step: int,
        reason: str = "explicit_close",
    ) -> None:
        """
        Close the currently active episode.
        """
        if self._active is None:
            return

        episode = self._active
        episode.close(step=step, time=0.0)

        self._trace.record_close(
            episode_id=episode.episode_id,
            step=step,
            start_step=episode.start_step,
            reason=reason,
        )

        self._active = None

    # --------------------------------------------------
    # Introspection (read-only)
    # --------------------------------------------------

    @property
    def active_episode(self) -> Optional[Episode]:
        return self._active

    def has_active_episode(self) -> bool:
        return self._active is not None

    @property
    def active_start_step(self) -> Optional[int]:
        return self._active.start_step if self._active else None

    def all_episodes(self) -> List[Episode]:
        return list(self._episodes)

    def last_episode(self) -> Optional[Episode]:
        return self._episodes[-1] if self._episodes else None

    def last_closed_episode(self) -> Optional[Episode]:
        for ep in reversed(self._episodes):
            if ep.closed:
                return ep
        return None

    def episode_count(self) -> int:
        return len(self._episodes)

    # --------------------------------------------------
    # Diagnostics / safety (debug-only)
    # --------------------------------------------------

    def sanity_check(self) -> None:
        """
        Internal consistency checks.

        This method asserts descriptive invariants only.
        """
        for ep in self._episodes:
            if ep.closed:
                assert ep.end_step is not None

            if ep.has_decision():
                assert ep.winner is not None or ep.decision_count > 0
