# engine/salience/pre_decision_adaptation/psmem.py

from collections import defaultdict
from typing import Dict, List

from .record import PSMRecord


class PSMem:
    """
    Pre-Decision Salience Memory (PSMem)

    Stores summaries of deliberation difficulty and produces a
    bounded salience bias for future encounters with similar contexts.

    This class:
      - does NOT decide
      - does NOT inject salience
      - does NOT run per timestep
      - does NOT store outcomes or rewards

    It only answers:
      "How hard was it to deliberate here before?"
    """

    def __init__(
        self,
        max_records_per_context: int = 20,
        gain: float = 0.05,
        max_bias: float = 0.30,
    ) -> None:
        # context_id -> list[PSMRecord]
        self._records: Dict[str, List[PSMRecord]] = defaultdict(list)

        self.max_records = max_records_per_context
        self.gain = gain
        self.max_bias = max_bias

    # ============================================================
    # Recording
    # ============================================================

    def record(self, rec: PSMRecord) -> None:
        """
        Store a deliberation summary for a given context.
        Older records are discarded once capacity is exceeded.
        """
        buf = self._records[rec.context_id]
        buf.append(rec)

        if len(buf) > self.max_records:
            self._records[rec.context_id] = buf[-self.max_records :]

    # ============================================================
    # Query
    # ============================================================

    def get_bias(self, context_id: str) -> float:
        """
        Return a bounded salience bias for a context.

        Bias increases with mean deliberation cost and is clipped
        to prevent runaway influence.
        """
        buf = self._records.get(context_id)
        if not buf:
            return 0.0

        mean_cost = sum(r.deliberation_cost for r in buf) / len(buf)

        bias = self.gain * mean_cost
        return min(bias, self.max_bias)

    # ============================================================
    # Introspection
    # ============================================================

    def context_count(self) -> int:
        return len(self._records)

    def record_count(self) -> int:
        return sum(len(v) for v in self._records.values())

    def stats(self) -> dict:
        """
        Lightweight diagnostics for debugging and visualization.
        """
        return {
            "contexts": self.context_count(),
            "records": self.record_count(),
            "max_records_per_context": self.max_records,
            "gain": self.gain,
            "max_bias": self.max_bias,
        }
