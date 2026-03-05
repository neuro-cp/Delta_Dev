from __future__ import annotations

from typing import Dict, Iterable, List


class WindowedActivationView:
    """
    Math-only windowing over semantic activation snapshots.

    CONTRACT:
    - Read-only
    - Deterministic
    - No aggregation across windows
    - No interpretation
    - Safe to remove
    """

    @staticmethod
    def sliding_window(
        *,
        history: List[Dict[str, float]],
        window_size: int,
    ) -> List[Dict[str, float]]:
        """
        Return the last N activation snapshots.

        If window_size <= 0, returns empty list.
        If history shorter than window, returns full history.
        """
        if window_size <= 0:
            return []

        if len(history) <= window_size:
            return list(history)

        return history[-window_size:]

    @staticmethod
    def exponential_window(
        *,
        history: List[Dict[str, float]],
        decay: float,
    ) -> List[Dict[str, float]]:
        """
        Apply exponential weighting to a history of activations.

        This does NOT aggregate values.
        It returns scaled snapshots preserving structure.

        decay: in (0, 1]; higher = slower decay
        """
        if not history:
            return []

        if decay <= 0 or decay > 1:
            raise ValueError("decay must be in (0, 1]")

        weighted: List[Dict[str, float]] = []
        weight = 1.0

        for snapshot in reversed(history):
            weighted.append(
                {k: v * weight for k, v in snapshot.items()}
            )
            weight *= decay

        return list(reversed(weighted))
