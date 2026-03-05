from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ValueTrace:
    """
    Diagnostic trace for tonic VTA value signal.

    CONTRACT:
    - Observational only
    - Append-only
    - No runtime influence
    """

    records: List[Dict[str, Any]] = field(default_factory=list)

    # ============================================================
    # Trace API
    # ============================================================

    def record_proposal(
        self,
        *,
        step: int,
        source: str,
        proposed_delta: float,
        accepted: bool,
        resulting_value: float,
        reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:
        """
        Record a value proposal attempt.
        """
        self.records.append(
            {
                "event": "proposal",
                "step": step,
                "source": source,
                "proposed_delta": float(proposed_delta),
                "accepted": bool(accepted),
                "resulting_value": float(resulting_value),
                "reason": reason,
                "note": note,
            }
        )

    def record_decay(
        self,
        *,
        step: int,
        value: float,
    ) -> None:
        """
        Record passive decay of the value signal.
        """
        self.records.append(
            {
                "event": "decay",
                "step": step,
                "value": float(value),
            }
        )

    # ============================================================
    # Accessors
    # ============================================================

    def clear(self) -> None:
        """Clear all trace records."""
        self.records.clear()

    def as_list(self) -> List[Dict[str, Any]]:
        """Return raw trace records (for CSV / pandas use)."""
        return list(self.records)

    def summary(self) -> Dict[str, Any]:
        """
        Lightweight summary for inspection.
        """
        if not self.records:
            return {
                "count": 0,
                "proposals": 0,
                "accepted": 0,
                "decays": 0,
            }

        proposals = [r for r in self.records if r["event"] == "proposal"]
        decays = [r for r in self.records if r["event"] == "decay"]

        return {
            "count": len(self.records),
            "proposals": len(proposals),
            "accepted": sum(1 for r in proposals if r["accepted"]),
            "decays": len(decays),
        }
