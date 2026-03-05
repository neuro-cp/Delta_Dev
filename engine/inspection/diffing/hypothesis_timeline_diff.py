from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Optional


# ---------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class HypothesisSummary:
    """
    Minimal, comparable snapshot of a hypothesis timeline.

    This object is intentionally:
    - shallow
    - descriptive
    - free of internal dynamics

    It is safe to compute offline and discard.
    """

    hypothesis_id: str

    # Whether the hypothesis stabilized at any point
    stabilized: bool

    # Step at which stabilization occurred (if any)
    stabilization_step: Optional[int]

    # Maximum observed activation during the timeline (if tracked)
    peak_activation: Optional[float]


# ---------------------------------------------------------------------
# Diff result
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class HypothesisTimelineDiff:
    """
    Descriptive diff between two hypothesis timeline snapshots.

    This object:
    - reports WHAT changed
    - does NOT explain WHY
    - does NOT judge importance
    """

    # Identity changes
    appeared: List[str]
    disappeared: List[str]

    # Property changes (per hypothesis)
    stabilization_changes: Dict[str, Dict[str, Optional[int]]]
    peak_activation_changes: Dict[str, Dict[str, Optional[float]]]


# ---------------------------------------------------------------------
# Diff function
# ---------------------------------------------------------------------

def diff_hypothesis_timelines(
    before: Dict[str, HypothesisSummary],
    after: Dict[str, HypothesisSummary],
) -> HypothesisTimelineDiff:
    """
    Compute a descriptive diff between two hypothesis summary mappings.

    Inputs are assumed to be:
    - keyed by hypothesis_id
    - derived from comparable timelines
    """

    before_ids: Set[str] = set(before.keys())
    after_ids: Set[str] = set(after.keys())

    # Identity-level changes
    appeared = sorted(after_ids - before_ids)
    disappeared = sorted(before_ids - after_ids)

    # Property-level changes
    stabilization_changes: Dict[str, Dict[str, Optional[int]]] = {}
    peak_activation_changes: Dict[str, Dict[str, Optional[float]]] = {}

    for hid in before_ids & after_ids:
        b = before[hid]
        a = after[hid]

        if b.stabilization_step != a.stabilization_step:
            stabilization_changes[hid] = {
                "before": b.stabilization_step,
                "after": a.stabilization_step,
            }

        if b.peak_activation != a.peak_activation:
            peak_activation_changes[hid] = {
                "before": b.peak_activation,
                "after": a.peak_activation,
            }

    return HypothesisTimelineDiff(
        appeared=appeared,
        disappeared=disappeared,
        stabilization_changes=stabilization_changes,
        peak_activation_changes=peak_activation_changes,
    )
