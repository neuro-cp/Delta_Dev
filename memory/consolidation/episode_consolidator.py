from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Protocol

from memory.episodic.episode_structure import Episode


class EpisodeSource(Protocol):
    @property
    def episodes(self) -> List[Episode]:
        ...


@dataclass(frozen=True)
class ConsolidationRecord:
    # Core identity
    episode_id: int

    # Temporal bounds
    start_step: int
    end_step: Optional[int]
    duration_steps: Optional[int]

    start_time: float
    end_time: Optional[float]
    duration_time: Optional[float]

    # Decision summary
    decision_count: int
    winner: Optional[str]
    confidence: Optional[float]

    # Derived temporal structure (Phase 5B enrichment)
    decision_steps: List[int]
    decision_times: List[float]

    inter_decision_intervals_steps: List[int]
    inter_decision_intervals_time: List[float]

    ended_by_decision: bool
    ended_by_timeout: bool

    tags: Dict[str, Any] = field(default_factory=dict)


class EpisodeConsolidator:
    """
    Offline episodic consolidation utility.

    Input: episode source (EpisodeTracker or any object exposing .episodes)
    Output: immutable ConsolidationRecords

    NO side effects.
    NO mutation.
    NO runtime access.
    """

    def __init__(self, source: EpisodeSource):
        self._source = source

    def consolidate(self) -> List[ConsolidationRecord]:
        records: List[ConsolidationRecord] = []

        for ep in self._source.episodes:
            if not ep.closed:
                continue
            records.append(self._consolidate_episode(ep))

        return records

    def _consolidate_episode(self, ep: Episode) -> ConsolidationRecord:
        decision_steps = [d["step"] for d in ep.decisions]
        decision_times = [
            d.get("time", 0.0) for d in ep.decisions
        ]


        interval_steps = self._intervals(decision_steps)
        interval_times = self._intervals(decision_times)

        ended_by_decision = ep.decision_count > 0
        ended_by_timeout = ep.closed and not ended_by_decision

        return ConsolidationRecord(
            episode_id=ep.episode_id,
            start_step=ep.start_step,
            end_step=ep.end_step,
            duration_steps=ep.duration_steps,
            start_time=ep.start_time,
            end_time=ep.end_time,
            duration_time=ep.duration_time,
            decision_count=ep.decision_count,
            winner=ep.winner,
            confidence=ep.confidence,
            decision_steps=decision_steps,
            decision_times=decision_times,
            inter_decision_intervals_steps=interval_steps,
            inter_decision_intervals_time=interval_times,
            ended_by_decision=ended_by_decision,
            ended_by_timeout=ended_by_timeout,
            tags=dict(ep.tags) if ep.tags else {},
        )

    def summary(self) -> Dict[str, Any]:
        records = self.consolidate()

        return {
            "episodes_consolidated": len(records),
            "episodes_with_decisions": sum(1 for r in records if r.decision_count > 0),
            "silent_episode_fraction": self._fraction(
                [r for r in records if r.decision_count == 0],
                total=len(records),
            ),
            "mean_decisions_per_episode": self._mean([r.decision_count for r in records]),
            "mean_duration_steps": self._mean([r.duration_steps for r in records if r.duration_steps is not None]),
            "mean_duration_time": self._mean([r.duration_time for r in records if r.duration_time is not None]),
            "mean_inter_decision_interval_steps": self._mean(
                [x for r in records for x in r.inter_decision_intervals_steps]
            ),
            "mean_inter_decision_interval_time": self._mean(
                [x for r in records for x in r.inter_decision_intervals_time]
            ),
        }

    @staticmethod
    def _intervals(values: List[float | int]) -> List[float | int]:
        if len(values) < 2:
            return []
        return [values[i] - values[i - 1] for i in range(1, len(values))]

    @staticmethod
    def _mean(values: List[Optional[float]]) -> Optional[float]:
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _fraction(values: List[Any], *, total: int) -> Optional[float]:
        if total == 0:
            return None
        return len(values) / total
