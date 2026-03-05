from __future__ import annotations

from typing import Dict, Any, Optional

from memory.attention.attention_field import AttentionField


class AttentionRuntimeHook:
    """
    Read-only runtime hook for attention.

    CONTRACT:
    - No runtime mutation
    - Emits bias suggestions only
    - Never applies gains
    """

    def __init__(
        self,
        *,
        field: AttentionField,
        gain_bias: Optional[Dict[str, float]] = None,
    ) -> None:
        self._field = field
        self._gain_bias = gain_bias or {}

    def snapshot(self) -> Dict[str, Any]:
        items = self._field.items()

        raw_gains = {i.key: i.gain for i in items}

        # Bias-adjusted gains are COMPUTED, not applied
        biased_gains = {
            key: raw_gains[key] * self._gain_bias.get(key, 1.0)
            for key in raw_gains
        }

        return {
            "count": len(items),
            "raw_gains": raw_gains,
            "biased_gains": biased_gains,
            "bias": dict(self._gain_bias),
        }
