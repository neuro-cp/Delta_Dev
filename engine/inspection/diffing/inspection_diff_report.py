from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.inspection.diffing.replay_plan_diff import ReplayPlanDiff
from engine.inspection.diffing.hypothesis_timeline_diff import HypothesisTimelineDiff


@dataclass(frozen=True)
class InspectionDiffReport:
    """
    Aggregated, read-only inspection diff.

    This report makes NO judgments.
    It only states what changed and where.
    """

    replay_plan_diff: ReplayPlanDiff
    hypothesis_timeline_diff: Optional[HypothesisTimelineDiff]

    @property
    def replay_changed(self) -> bool:
        return not (
            self.replay_plan_diff.same_selection
            and self.replay_plan_diff.same_ordering
        )

    @property
    def cognition_changed(self) -> bool:
        if self.hypothesis_timeline_diff is None:
            return False

        h = self.hypothesis_timeline_diff
        return any([
            h.appeared,
            h.disappeared,
            h.stabilization_changes,
            h.peak_activation_changes,
        ])
