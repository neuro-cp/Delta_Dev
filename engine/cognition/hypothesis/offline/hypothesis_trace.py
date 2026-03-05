from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Iterable, Optional


# ============================================================
# Trace record (immutable, forensic)
# ============================================================

@dataclass(frozen=True)
class HypothesisTraceRecord:
    """
    Immutable forensic record of a hypothesis-related event.

    This record:
    - is append-only
    - is offline only
    - carries no authority
    - is safe to export or discard

    It describes WHAT occurred, not WHY it mattered.
    """

    step: int
    hypothesis_id: str
    event: str              # e.g. "support", "activation", "suppression", "stabilized", "bias"
    payload: Dict[str, Any]


# ============================================================
# Hypothesis trace buffer
# ============================================================

class HypothesisTrace:
    """
    Append-only offline trace for hypothesis processing.

    Responsibilities:
    - Record hypothesis dynamics and events
    - Provide read-only access for inspection and tests

    Non-responsibilities:
    - No interpretation
    - No aggregation
    - No mutation of hypotheses
    """

    def __init__(self) -> None:
        self._records: List[HypothesisTraceRecord] = []

    # --------------------------------------------------
    # Recording helpers
    # --------------------------------------------------

    def record(
        self,
        *,
        step: int,
        hypothesis_id: str,
        event: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Append a new trace record.
        """
        self._records.append(
            HypothesisTraceRecord(
                step=int(step),
                hypothesis_id=str(hypothesis_id),
                event=str(event),
                payload=dict(payload),
            )
        )

    # --------------------------------------------------
    # Read-only accessors
    # --------------------------------------------------

    def records(self) -> List[HypothesisTraceRecord]:
        """
        Return a snapshot list of all trace records.
        """
        return list(self._records)

    def iter(self) -> Iterable[HypothesisTraceRecord]:
        """
        Iterate over records in insertion order.
        """
        yield from self._records

    def for_hypothesis(self, hypothesis_id: str) -> List[HypothesisTraceRecord]:
        """
        Return all records associated with a given hypothesis.
        """
        return [
            r for r in self._records
            if r.hypothesis_id == hypothesis_id
        ]

    def recent(self, n: int = 10) -> List[HypothesisTraceRecord]:
        """
        Return the most recent n records.
        """
        if n <= 0:
            return []
        return self._records[-n:]

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """
        Return a compact diagnostic summary.
        """
        return {
            "total_records": len(self._records),
            "events_by_type": self._count_by("event"),
            "hypotheses_seen": sorted(
                {r.hypothesis_id for r in self._records}
            ),
        }

    def _count_by(self, field: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self._records:
            key = getattr(r, field)
            counts[key] = counts.get(key, 0) + 1
        return counts
