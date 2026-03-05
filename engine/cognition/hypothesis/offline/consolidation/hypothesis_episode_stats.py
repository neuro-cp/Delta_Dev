from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from memory.episodic.episode import Episode
from engine.cognition.hypothesis.offline.inspection.hypothesis_timeline import (
    HypothesisTimelineBundle,
    HypothesisTimeline,
)


# --------------------------------------------------
# Per-hypothesis episode statistics
# --------------------------------------------------

@dataclass(frozen=True)
class HypothesisEpisodeStats:
    """
    Descriptive statistics for a single hypothesis across episodes.

    CONTRACT:
    - Offline only
    - Purely descriptive
    - No persistence
    - No authority
    """

    hypothesis_id: str

    episode_count: int
    stabilized_episode_count: int

    first_seen_episode: Optional[int]
    last_seen_episode: Optional[int]

    mean_activation_peak: float
    mean_support_peak: float

    stabilized_fraction: float


# --------------------------------------------------
# Multi-hypothesis stats bundle
# --------------------------------------------------

@dataclass(frozen=True)
class HypothesisEpisodeStatsBundle:
    """
    Container for all hypothesis episode stats.

    Pure data.
    """
    stats: Dict[str, HypothesisEpisodeStats]

    def get(self, hypothesis_id: str) -> Optional[HypothesisEpisodeStats]:
        return self.stats.get(hypothesis_id)

    def all(self) -> List[HypothesisEpisodeStats]:
        return list(self.stats.values())


# --------------------------------------------------
# Stats builder
# --------------------------------------------------

class HypothesisEpisodeStatsBuilder:
    """
    Builds descriptive hypothesis statistics across episodic boundaries.

    INPUTS:
    - Episodic structure (episodes)
    - Hypothesis timelines (offline cognition output)

    OUTPUT:
    - Descriptive statistics only

    CONTRACT:
    - Read-only
    - Deterministic
    - Safe to recompute
    """

    def __init__(
        self,
        *,
        episodes: List[Episode],
        timelines: HypothesisTimelineBundle,
    ) -> None:
        self._episodes = episodes
        self._timelines = timelines

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def build(self) -> HypothesisEpisodeStatsBundle:
        stats: Dict[str, HypothesisEpisodeStats] = {}

        for timeline in self._timelines.all_timelines():
            stats[timeline.hypothesis_id] = self._compute_for_hypothesis(timeline)

        return HypothesisEpisodeStatsBundle(stats=stats)

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _compute_for_hypothesis(
        self,
        timeline: HypothesisTimeline,
    ) -> HypothesisEpisodeStats:

        episode_indices_seen: List[int] = []
        stabilized_episodes = 0

        activation_peaks: List[float] = []
        support_peaks: List[float] = []

        # --------------------------------------------------
        # Iterate episodes
        # --------------------------------------------------

        for idx, ep in enumerate(self._episodes):
            # Activation samples inside this episode
            samples = [
                a
                for a in timeline.activations
                if ep.start_step <= a.step <= ep.end_step
            ]

            if not samples:
                continue

            episode_indices_seen.append(idx)

            activation_peaks.append(max(a.activation for a in samples))
            support_peaks.append(max(a.support for a in samples))

            if (
                timeline.stabilization is not None
                and ep.start_step
                <= timeline.stabilization.step
                <= ep.end_step
            ):
                stabilized_episodes += 1

        episode_count = len(episode_indices_seen)

        if episode_count == 0:
            return HypothesisEpisodeStats(
                hypothesis_id=timeline.hypothesis_id,
                episode_count=0,
                stabilized_episode_count=0,
                first_seen_episode=None,
                last_seen_episode=None,
                mean_activation_peak=0.0,
                mean_support_peak=0.0,
                stabilized_fraction=0.0,
            )

        return HypothesisEpisodeStats(
            hypothesis_id=timeline.hypothesis_id,
            episode_count=episode_count,
            stabilized_episode_count=stabilized_episodes,
            first_seen_episode=min(episode_indices_seen),
            last_seen_episode=max(episode_indices_seen),
            mean_activation_peak=sum(activation_peaks) / len(activation_peaks),
            mean_support_peak=sum(support_peaks) / len(support_peaks),
            stabilized_fraction=stabilized_episodes / episode_count,
        )
