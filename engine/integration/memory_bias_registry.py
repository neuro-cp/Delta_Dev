from __future__ import annotations

from typing import Dict, Any, Optional


class MemoryBiasRegistry:
    """
    Central registry for cognitive bias suggestions.

    CONTRACT:
    - Collects bias suggestions only
    - No application of bias
    - Read-only exposure
    - Deterministic
    """

    def __init__(self) -> None:
        self._attention_bias: Dict[str, Dict[str, float]] = {}
        self._working_memory_bias: Dict[str, float] = {}

    # --------------------------------------------------
    # Registration
    # --------------------------------------------------
    def register_attention_bias(
        self,
        *,
        source: str,
        bias: Dict[str, float],
    ) -> None:
        """
        Register attention gain bias suggestions.
        """
        self._attention_bias[source] = dict(bias)

    def register_working_memory_decay_bias(
        self,
        *,
        source: str,
        bias: float,
    ) -> None:
        """
        Register working-memory decay bias (scalar).
        """
        self._working_memory_bias[source] = bias

    # --------------------------------------------------
    # Read-only access
    # --------------------------------------------------
    def attention_bias(self) -> Dict[str, Dict[str, float]]:
        return dict(self._attention_bias)

    def working_memory_decay_bias(self) -> Dict[str, float]:
        return dict(self._working_memory_bias)

    def snapshot(self) -> Dict[str, Any]:
        """
        Inspection-safe snapshot.
        """
        return {
            "attention_bias": self.attention_bias(),
            "working_memory_decay_bias": self.working_memory_decay_bias(),
        }

    # --------------------------------------------------
    # Lifecycle
    # --------------------------------------------------
    def clear(self) -> None:
        """
        Clear all registered biases.
        """
        self._attention_bias.clear()
        self._working_memory_bias.clear()
