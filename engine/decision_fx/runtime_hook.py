# engine/decision_fx/runtime_hook.py
from __future__ import annotations

from typing import Dict, Any, Optional


class DecisionRuntimeHook:
    """
    Decision → Runtime interface (read-only).

    ROLE:
    - Translate DecisionEffects into runtime-safe gain modifiers
    - No learning
    - No memory (except last snapshot for observability)
    - Can be bypassed entirely

    APPLIED VIA:
    - Connectivity gain
    - Thalamic relay gain
    - Optional channel suppression
    """

    def __init__(self) -> None:
        self._active: bool = False
        self._snapshot: Dict[str, Any] = {}

    # --------------------------------------------------
    # Ingest effects (from DecisionEffects)
    # --------------------------------------------------

    def ingest(self, effects: Dict[str, Any]) -> None:
        if not effects:
            self._active = False
            self._snapshot = {}
            return

        self._active = True
        self._snapshot = dict(effects)

    # --------------------------------------------------
    # Runtime queries (SAFE)
    # --------------------------------------------------

    def thalamic_gain(self) -> float:
        if not self._active:
            return 1.0
        return float(self._snapshot.get("thalamic_gain", 1.0))

    def region_gain(self, region: str) -> float:
        if not self._active:
            return 1.0
        rg = self._snapshot.get("region_gain", {})
        return float(rg.get(region, 1.0))

    def channel_suppression(self, channel: str) -> float:
        if not self._active:
            return 1.0
        sup = self._snapshot.get("suppress_channels", {})
        return float(sup.get(channel, 1.0))

    def lock_action(self) -> bool:
        if not self._active:
            return False
        return bool(self._snapshot.get("lock_action", False))

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return dict(self._snapshot)
