from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class Episode:
    """
    Passive representation of a single cognitive episode.

    An episode is a bounded, descriptive temporal container:
    - It has a start
    - It may have an end
    - It may contain one or more decision annotations
    - It carries no authority and performs no actions

    This object is intentionally inert and observational only.
    """

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------
    episode_id: int

    # --------------------------------------------------
    # Temporal bounds
    # --------------------------------------------------
    start_step: int
    start_time: float

    end_step: Optional[int] = None
    end_time: Optional[float] = None

    # --------------------------------------------------
    # Decision annotations (append-only, observational)
    # --------------------------------------------------
    decisions: List[Dict[str, Any]] = field(default_factory=list)

    # --------------------------------------------------
    # Episode state
    # --------------------------------------------------
    closed: bool = False

    # --------------------------------------------------
    # Derived metadata (anchored on first decision)
    # --------------------------------------------------
    winner: Optional[str] = None
    confidence: Optional[float] = None

    # --------------------------------------------------
    # Optional free-form tags (pure annotation)
    # --------------------------------------------------
    tags: Dict[str, Any] = field(default_factory=dict)

    # --------------------------------------------------
    # Lifecycle helpers (state-only, non-authoritative)
    # --------------------------------------------------
    def mark_decision(
        self,
        *,
        step: int,
        time: float,
        winner: Optional[str] = None,
        confidence: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Annotate the episode with a decision event.

        Decisions are append-only records.
        The first decision anchors episode-level metadata
        (winner, confidence). Subsequent decisions do not
        overwrite episode identity.
        """
        record: Dict[str, Any] = {
            "step": step,
            "time": time,
            "winner": winner,
            "confidence": confidence,
        }

        if payload:
            record.update(payload)

        self.decisions.append(record)

        # First-decision anchoring (deterministic, descriptive)
        if self.winner is None:
            self.winner = winner
            self.confidence = confidence

    def close(
        self,
        *,
        step: int,
        time: float,
    ) -> None:
        """
        Close the episode.

        Records termination metadata only.
        No downstream effects are triggered.
        """
        self.end_step = step
        self.end_time = time
        self.closed = True

    # --------------------------------------------------
    # Introspection helpers (derived, read-only)
    # --------------------------------------------------
    @property
    def decision_count(self) -> int:
        return len(self.decisions)

    @property
    def duration_steps(self) -> Optional[int]:
        if self.end_step is None:
            return None
        return self.end_step - self.start_step

    @property
    def duration_time(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def has_decision(self) -> bool:
        return bool(self.decisions)

    def is_active(self) -> bool:
        return not self.closed
