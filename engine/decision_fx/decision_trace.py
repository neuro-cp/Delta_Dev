# engine/decision_fx/decision_trace.py
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional


class DecisionTrace:
    """
    Append-only causal trace for decision events.

    PURPOSE:
    - Explain *why* a decision happened
    - Capture bias + effects + runtime hooks
    - Enable replay and forensic inspection

    HARD RULES:
    - No feedback into runtime
    - No mutation of other subsystems
    - No timing control
    """

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # Record decision event
    # --------------------------------------------------

    def record(
        self,
        *,
        step: int,
        time: float,
        winner: Optional[str],
        dominance: Dict[str, float],
        delta: float,
        relief: float,
        bias: Optional[Dict[str, float]] = None,
        effects: Optional[Dict[str, Any]] = None,
        runtime_hook: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = {
            "step": int(step),
            "time": float(time),
            "winner": winner,
            "dominance": dict(dominance),
            "delta": float(delta),
            "relief": float(relief),
        }

        if bias:
            event["bias"] = dict(bias)

        if effects:
            event["effects"] = dict(effects)

        if runtime_hook:
            event["runtime_hook"] = dict(runtime_hook)

        self._events.append(event)

    # --------------------------------------------------
    # Accessors
    # --------------------------------------------------

    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def last(self) -> Optional[Dict[str, Any]]:
        return self._events[-1] if self._events else None

    def clear(self) -> None:
        self._events.clear()

    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self._events, indent=indent)

    def dump(self) -> List[Dict[str, Any]]:
        """
        Alias for compatibility with command server / diagnostics.
        """
        return self.events()
