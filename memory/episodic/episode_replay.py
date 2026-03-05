from __future__ import annotations

from typing import Iterator, Callable, Optional, Dict, Any, List

from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTrace

# Salience is an external, read-only observational log
from engine.salience.salience_trace import SalienceTrace


class EpisodeReplay:
    """
    Read-only episodic replay utility.

    Consumes:
    - a snapshot list of Episodes (structure)
    - an EpisodeTrace (episodic events)
    - an optional SalienceTrace (deviation observations)

    Guarantees:
    - NO mutation
    - NO runtime coupling
    - NO interpretation
    - NO authority

    This class exists solely to ALIGN timelines offline.
    """

    def __init__(
        self,
        *,
        episodes: List[Episode],
        episode_trace: EpisodeTrace,
        salience_trace: Optional[SalienceTrace] = None,
    ) -> None:
        # Snapshot to prevent external mutation
        self._episodes = list(episodes)
        self._episode_trace = episode_trace
        self._salience_trace = salience_trace

    # --------------------------------------------------
    # Core accessors
    # --------------------------------------------------

    def episodes(self) -> List[Episode]:
        return list(self._episodes)

    def closed_episodes(self) -> List[Episode]:
        return [ep for ep in self._episodes if ep.closed]

    def active_episode(self) -> Optional[Episode]:
        for ep in reversed(self._episodes):
            if not ep.closed:
                return ep
        return None

    # --------------------------------------------------
    # Iterators
    # --------------------------------------------------

    def iter_episodes(self) -> Iterator[Episode]:
        yield from self._episodes

    def iter_closed(self) -> Iterator[Episode]:
        for ep in self._episodes:
            if ep.closed:
                yield ep

    # --------------------------------------------------
    # Decision-focused views
    # --------------------------------------------------

    def episodes_with_decisions(self) -> List[Episode]:
        return [ep for ep in self._episodes if ep.has_decision()]

    def iter_decision_events(self) -> Iterator[Dict[str, Any]]:
        for ep in self._episodes:
            for d in ep.decisions:
                yield {
                    "episode_id": ep.episode_id,
                    "episode_start_step": ep.start_step,
                    "episode_start_time": ep.start_time,
                    **d,
                }

    # --------------------------------------------------
    # Episodic trace alignment
    # --------------------------------------------------

    def episode_events(self, episode_id: int):
        """
        Return episodic trace records for a given episode_id.
        """
        return [
            r for r in self._episode_trace.records()
            if r.episode_id == episode_id
        ]

    # --------------------------------------------------
    # Salience trace alignment (READ-ONLY)
    # --------------------------------------------------

    def salience_for_episode(self, ep: Episode):
        """
        Return salience trace records whose step falls within
        the episode's lifetime.

        Salience is aligned by STEP RANGE, not by episode_id.
        """
        if self._salience_trace is None:
            return []

        if ep.start_step is None or ep.end_step is None:
            return []

        start = ep.start_step
        end = ep.end_step

        return [
            r for r in self._salience_trace.records()
            if start <= r.step <= end
        ]

    # --------------------------------------------------
    # Combined replay
    # --------------------------------------------------

    def replay(self):
        """
        Yield closed episodes with their aligned traces.

        Output tuple:
        (Episode, episode_events, salience_events)
        """
        for ep in self.closed_episodes():
            yield (
                ep,
                self.episode_events(ep.episode_id),
                self.salience_for_episode(ep),
            )

    # --------------------------------------------------
    # Summaries
    # --------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        closed = [ep for ep in self._episodes if ep.closed]

        return {
            "total_episodes": len(self._episodes),
            "closed_episodes": len(closed),
            "episodes_with_decisions": sum(1 for ep in self._episodes if ep.has_decision()),
            "total_decisions": sum(len(ep.decisions) for ep in self._episodes),
            "mean_duration_steps": self._mean(
                [ep.duration_steps for ep in closed if ep.duration_steps is not None]
            ),
            "mean_duration_time": self._mean(
                [ep.duration_time for ep in closed if ep.duration_time is not None]
            ),
        }

    # --------------------------------------------------
    # Projections
    # --------------------------------------------------

    def project(
        self,
        fn: Callable[[Episode], Any],
        *,
        closed_only: bool = True,
    ) -> List[Any]:
        eps = self.closed_episodes() if closed_only else self.episodes()
        return [fn(ep) for ep in eps]

    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------

    @staticmethod
    def _mean(values: List[float]) -> Optional[float]:
        if not values:
            return None
        return sum(values) / len(values)
