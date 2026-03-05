from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.inspection.diffing.hypothesis_timeline_diff import HypothesisTimelineDiff


@dataclass(frozen=True)
class DiffReport:
    """
    Immutable inspection artifact describing differences
    between two cognition inspection snapshots.

    This object:
    - is descriptive only
    - carries no authority
    - is safe to serialize, discard, and recompute
    """

    # High-level flags
    replay_changed: bool
    cognition_changed: bool

    # Optional detailed diffs
    hypothesis_diff: Optional[HypothesisTimelineDiff] = None

    def has_any_change(self) -> bool:
        """
        Convenience helper for inspection tooling.
        """
        return self.replay_changed or self.cognition_changed
