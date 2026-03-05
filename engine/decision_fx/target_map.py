from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DecisionTargets:
    """
    Read-only mapping output.

    - focus_regions: regions to receive mild gain (focus)
    - suppress_regions: regions to receive mild suppressive gain (or inhibition hint)
    - region_gain: explicit per-region gain overrides (multiplicative, e.g., 1.05)
    - notes: debug trace string
    """
    focus_regions: List[str]
    suppress_regions: List[str]
    region_gain: Dict[str, float]
    notes: str


class TargetMap:
    """
    Translate decision winner labels (often 'D1'/'D2') into concrete runtime targets.

    HARD RULES:
    - Mapping only. No learning. No dynamics. No state.
    - Conservative gains only (close to 1.0).
    """

    def __init__(
        self,
        *,
        focus_gain: float = 1.04,
        suppress_gain: float = 0.98,
        default_focus: Optional[List[str]] = None,
        default_suppress: Optional[List[str]] = None,
        winner_to_focus: Optional[Dict[str, List[str]]] = None,
        winner_to_suppress: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.focus_gain = float(focus_gain)
        self.suppress_gain = float(suppress_gain)

        self.default_focus = list(default_focus) if default_focus is not None else ["pfc"]
        self.default_suppress = list(default_suppress) if default_suppress is not None else []

        # Minimal sane defaults: D1/D2 still map to *real* regions.
        self.winner_to_focus = dict(winner_to_focus) if winner_to_focus is not None else {
            "D1": ["pfc"],
            "D2": ["pfc"],
        }
        self.winner_to_suppress = dict(winner_to_suppress) if winner_to_suppress is not None else {
            "D1": [],
            "D2": [],
        }

    def resolve(self, *, winner: Optional[str]) -> DecisionTargets:
        if winner is None:
            return DecisionTargets([], [], {}, "winner=None → no targets")

        focus = self.winner_to_focus.get(winner, self.default_focus)
        suppress = self.winner_to_suppress.get(winner, self.default_suppress)

        region_gain: Dict[str, float] = {}
        for r in focus:
            region_gain[r] = max(region_gain.get(r, 1.0), self.focus_gain)

        # If a region is both focused and suppressed, focus wins (conservative rule).
        for r in suppress:
            if r not in region_gain:
                region_gain[r] = min(region_gain.get(r, 1.0), self.suppress_gain)

        return DecisionTargets(
            focus_regions=list(focus),
            suppress_regions=list(suppress),
            region_gain=region_gain,
            notes=f"winner={winner} focus={focus} suppress={suppress}",
        )
