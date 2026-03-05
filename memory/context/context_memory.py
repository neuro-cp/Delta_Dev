from __future__ import annotations

from typing import Dict, List, Optional
import time

from memory.context.context_trace import ContextTrace


class ContextMemory:
    """
    Context memory store.

    PURPOSE:
    - Hold short-to-mid timescale contextual relevance
    - Support decay and pruning
    - Enable query-based recall

    NON-GOALS:
    - No learning rules
    - No reinforcement logic
    - No decision authority
    - No runtime coupling
    """

    def __init__(
        self,
        decay_tau: float = 30.0,
        max_traces: int = 1024,
        min_strength: float = 1e-4,
    ):
        """
        decay_tau:
            Time constant (seconds) for exponential decay.
        max_traces:
            Hard cap on number of stored traces.
        min_strength:
            Traces below this are pruned.
        """
        self.decay_tau = float(decay_tau)
        self.max_traces = int(max_traces)
        self.min_strength = float(min_strength)

        self._traces: List[ContextTrace] = []

    # ============================================================
    # Core API
    # ============================================================

    def add(self, trace: ContextTrace) -> None:
        """
        Insert a new trace.
        Oldest / weakest traces are pruned if over capacity.
        """
        self._traces.append(trace)
        self._prune_capacity()

    def query(self, context: Dict[str, str]) -> List[ContextTrace]:
        """
        Return all traces matching the given context signature,
        sorted by descending strength.
        """
        matches = [t for t in self._traces if t.matches(context)]
        return sorted(matches, key=lambda t: t.strength, reverse=True)

    def all(self) -> List[ContextTrace]:
        """
        Return all traces (read-only copy).
        """
        return list(self._traces)

    # ============================================================
    # Time evolution
    # ============================================================

    def step(self, dt: float) -> None:
        """
        Advance time and apply decay.
        """
        if dt <= 0.0:
            return

        now = time.time()
        new_traces: List[ContextTrace] = []

        for t in self._traces:
            age = t.age(now)
            decay = self._decay_factor(age)
            new_strength = t.strength * decay

            if new_strength >= self.min_strength:
                new_traces.append(
                    ContextTrace(
                        trace_id=t.trace_id,
                        context=dict(t.context),
                        strength=new_strength,
                        created_at=t.created_at,
                        source_region=t.source_region,
                        source_channel=t.source_channel,
                    )
                )

        self._traces = new_traces
        self._prune_capacity()

    # ============================================================
    # Internal helpers
    # ============================================================

    def _decay_factor(self, age: float) -> float:
        """
        Exponential decay based on trace age.
        """
        if self.decay_tau <= 0.0:
            return 1.0
        return pow(2.718281828, -age / self.decay_tau)

    def _prune_capacity(self) -> None:
        """
        Enforce max_traces by dropping weakest traces.
        """
        if len(self._traces) <= self.max_traces:
            return

        self._traces.sort(key=lambda t: t.strength, reverse=True)
        self._traces = self._traces[: self.max_traces]

    # ============================================================
    # Diagnostics
    # ============================================================

    def stats(self) -> Dict[str, float]:
        """
        Lightweight diagnostics for instrumentation.
        """
        if not self._traces:
            return {
                "count": 0,
                "mean_strength": 0.0,
                "max_strength": 0.0,
            }

        strengths = [t.strength for t in self._traces]
        return {
            "count": len(self._traces),
            "mean_strength": sum(strengths) / len(strengths),
            "max_strength": max(strengths),
        }
