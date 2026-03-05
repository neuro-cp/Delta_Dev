from __future__ import annotations

"""
Offline certification test for inspection diffing.

This test verifies:
- ReplayPlan diffs are detected correctly
- Hypothesis timeline diffs are detected independently
- No authority or semantics are implied

This is a PURE inspection test.
"""

from engine.replay.requests.replay_request import ReplayRequest
from engine.replay.scheduling.replay_plan import ReplayPlan

from engine.inspection.diffing.replay_plan_diff import diff_replay_plans
from engine.inspection.diffing.hypothesis_timeline_diff import (
    HypothesisSummary,
    diff_hypothesis_timelines,
)
from engine.inspection.diffing.inspection_diff_report import InspectionDiffReport


def test_inspection_diff_basic() -> None:
    # --------------------------------------------------
    # Replay plans (identical)
    # --------------------------------------------------
    request = ReplayRequest(reason="manual", requested_step=100)

    plan_a = ReplayPlan(
        request=request,
        selected_episode_ids=["ep_005", "ep_004", "ep_002"],
        eligibility_reasons={
            "ep_002": "eligible",
            "ep_004": "eligible",
            "ep_005": "eligible",
        },
    )

    plan_b = ReplayPlan(
        request=request,
        selected_episode_ids=["ep_005", "ep_004", "ep_002"],
        eligibility_reasons={
            "ep_002": "eligible",
            "ep_004": "eligible",
            "ep_005": "eligible",
        },
    )

    replay_diff = diff_replay_plans(plan_a, plan_b)

    # Replay should be identical
    assert replay_diff.same_selection
    assert replay_diff.same_ordering
    assert replay_diff.added_episode_ids == []
    assert replay_diff.removed_episode_ids == []

    # --------------------------------------------------
    # Hypothesis timelines (one changed)
    # --------------------------------------------------
    before = {
        "H1": HypothesisSummary(
            hypothesis_id="H1",
            stabilized=True,
            stabilization_step=50,
            peak_activation=0.82,
        )
    }

    after = {
        "H1": HypothesisSummary(
            hypothesis_id="H1",
            stabilized=True,
            stabilization_step=60,  # changed
            peak_activation=0.82,
        )
    }

    hypothesis_diff = diff_hypothesis_timelines(before, after)

    # Cognition changed, replay did not
    assert hypothesis_diff.appeared == []
    assert hypothesis_diff.disappeared == []
    assert hypothesis_diff.stabilization_changes["H1"] == {
        "before": 50,
        "after": 60,
    }

    # --------------------------------------------------
    # Aggregated inspection report
    # --------------------------------------------------
    report = InspectionDiffReport(
        replay_plan_diff=replay_diff,
        hypothesis_timeline_diff=hypothesis_diff,
    )

    assert report.replay_changed is False
    assert report.cognition_changed is True

    # --------------------------------------------------
    # Human-readable confirmation
    # --------------------------------------------------
    print("\n=== INSPECTION DIFF CERTIFICATION ===")
    print("Replay changed:", report.replay_changed)
    print("Cognition changed:", report.cognition_changed)
    print("Stabilization delta:", hypothesis_diff.stabilization_changes)
