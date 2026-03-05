from __future__ import annotations

from typing import Dict

from engine.inspection.diffing.diff_report import DiffReport
from engine.inspection.diffing.hypothesis_timeline_diff import (
    HypothesisSummary,
    HypothesisTimelineDiff,
    diff_hypothesis_timelines,
)


class DiffRunner:
    """
    Offline diff orchestration.

    This runner:
    - compares inspection artifacts
    - produces a descriptive DiffReport

    It does NOT:
    - influence replay
    - influence cognition
    - influence memory
    """

    def diff_hypothesis_summaries(
        self,
        *,
        before: Dict[str, HypothesisSummary],
        after: Dict[str, HypothesisSummary],
    ) -> DiffReport:
        """
        Diff two hypothesis summary mappings.

        Inputs are assumed to be derived from
        comparable cognition timelines.
        """

        hypothesis_diff: HypothesisTimelineDiff = diff_hypothesis_timelines(
            before=before,
            after=after,
        )

        cognition_changed = bool(
            hypothesis_diff.appeared
            or hypothesis_diff.disappeared
            or hypothesis_diff.stabilization_changes
            or hypothesis_diff.peak_activation_changes
        )

        return DiffReport(
            replay_changed=False,   # replay semantics are external
            cognition_changed=cognition_changed,
            hypothesis_diff=hypothesis_diff,
        )
