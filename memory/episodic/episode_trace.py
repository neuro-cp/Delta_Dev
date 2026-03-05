from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class EpisodeTraceRecord:
    """
    Immutable trace record for episodic events.
    """
    event: str               # "start", "decision", "close"
    episode_id: int
    step: int
    payload: Dict[str, Any]


class EpisodeTrace:
    """
    Append-only, read-only episodic trace.

    This is a forensic log, not a control surface.
    """

    def __init__(self) -> None:
        self._records: List[EpisodeTraceRecord] = []

    # --------------------------------------------------
    # Record events (backward-compatible)
    # --------------------------------------------------
    def record_start(
        self,
        *,
        episode_id: int,
        step: int,
        time: float | None = None,
        reason: Optional[str] = None,
        **extra: Any,
    ) -> None:
        payload: Dict[str, Any] = {}

        if time is not None:
            payload["time"] = time

        if reason is not None:
            payload["reason"] = reason

        payload.update(extra)

        self._records.append(
            EpisodeTraceRecord(
                event="start",
                episode_id=episode_id,
                step=step,
                payload=payload,
            )
        )

    def record_decision(
        self,
        *,
        episode_id: int,
        step: int,
        time: float | None = None,
        winner: str | None = None,
        confidence: float | None = None,
        **extra: Any,
    ) -> None:
        payload: Dict[str, Any] = {}

        if time is not None:
            payload["time"] = time
        if winner is not None:
            payload["winner"] = winner
        if confidence is not None:
            payload["confidence"] = confidence

        payload.update(extra)

        self._records.append(
            EpisodeTraceRecord(
                event="decision",
                episode_id=episode_id,
                step=step,
                payload=payload,
            )
        )

    def record_close(
        self,
        *,
        episode_id: int,
        step: int,
        time: float | None = None,
        duration_steps: int | None = None,
        duration_time: float | None = None,
        decision_count: int | None = None,
        reason: Optional[str] = None,
        **extra: Any,
    ) -> None:
        payload: Dict[str, Any] = {}

        if time is not None:
            payload["time"] = time
        if duration_steps is not None:
            payload["duration_steps"] = duration_steps
        if duration_time is not None:
            payload["duration_time"] = duration_time
        if decision_count is not None:
            payload["decision_count"] = decision_count
        if reason is not None:
            payload["reason"] = reason

        payload.update(extra)

        self._records.append(
            EpisodeTraceRecord(
                event="close",
                episode_id=episode_id,
                step=step,
                payload=payload,
            )
        )

    # --------------------------------------------------
    # Accessors
    # --------------------------------------------------
    def records(self) -> List[EpisodeTraceRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()
