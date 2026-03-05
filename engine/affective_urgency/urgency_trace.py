from __future__ import annotations

from typing import Dict, Any, List


class UrgencyTrace:
    """
    Read-only trace for affective urgency.

    Records urgency evolution over time for
    debugging, plotting, and audit.
    """

    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # Recording
    # --------------------------------------------------

    def record(
        self,
        *,
        time: float,
        step: int,
        urgency: float,
        delta: float,
        allowed: bool,
        reason: str,
        gate_relief: float | None = None,
    ) -> None:
        """
        Append a trace record.

        All fields are observational.
        """

        self._records.append(
            {
                "time": float(time),
                "step": int(step),
                "urgency": float(urgency),
                "delta": float(delta),
                "allowed": bool(allowed),
                "reason": str(reason),
                "gate_relief": None if gate_relief is None else float(gate_relief),
            }
        )

    # --------------------------------------------------
    # Accessors
    # --------------------------------------------------

    def records(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def last(self) -> Dict[str, Any] | None:
        if not self._records:
            return None
        return self._records[-1]

    def clear(self) -> None:
        self._records.clear()

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        if not self._records:
            return {
                "count": 0,
                "max_urgency": 0.0,
                "mean_urgency": 0.0,
            }

        urgencies = [r["urgency"] for r in self._records]

        return {
            "count": len(self._records),
            "max_urgency": max(urgencies),
            "mean_urgency": sum(urgencies) / len(urgencies),
        }
