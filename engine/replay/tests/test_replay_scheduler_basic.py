from __future__ import annotations

"""
Offline certification test for replay scheduling.

This test verifies:
- Deterministic selection
- Scarcity enforcement
- Full auditability via report

This test has NO runtime, episodic, or cognition dependencies.
"""

from engine.replay.requests.replay_request import ReplayRequest
from engine.replay.scheduling.replay_scheduler import ReplayScheduler
from engine.replay.inspection.replay_schedule_report import ReplayScheduleReport


def test_replay_scheduler_basic() -> None:
    # --------------------------------------------------
    # Fake episode metadata (stand-in for Episodic layer)
    # --------------------------------------------------
    episodes_meta = {
        "ep_001": {"length": 5, "decision_count": 0, "end_step": 10},
        "ep_002": {"length": 12, "decision_count": 1, "end_step": 25},
        "ep_003": {"length": 1, "decision_count": 0, "end_step": 30},
        "ep_004": {"length": 20, "decision_count": 2, "end_step": 45},
        "ep_005": {"length": 8, "decision_count": 1, "end_step": 60},
        "ep_006": {"length": 0, "decision_count": 0, "end_step": 70},  # invalid
    }

    # --------------------------------------------------
    # Replay request (manual / nap / stress etc.)
    # --------------------------------------------------
    request = ReplayRequest(
        reason="manual_request",
        requested_step=100,
        urgency=0.5,
    )

    # --------------------------------------------------
    # Scheduler (scarcity enforced)
    # --------------------------------------------------
    scheduler = ReplayScheduler(max_episodes=3)

    plan = scheduler.schedule(
        request=request,
        episodes_meta=episodes_meta,
    )

    report = ReplayScheduleReport.from_plan(plan)

    # --------------------------------------------------
    # Assertions: determinism + scarcity
    # --------------------------------------------------
    assert len(plan.selected_episode_ids) <= 3

    # Newest episodes should be preferred
    assert plan.selected_episode_ids == [
        "ep_005",
        "ep_004",
        "ep_002",
    ]

    # Invalid / excluded episodes must be explainable
    assert "ep_006" in report.excluded_episode_ids
    assert report.eligibility_reasons["ep_006"] == "episode_too_short"

    # --------------------------------------------------
    # Human-readable output (intentional)
    # --------------------------------------------------
    print("\n=== REPLAY SCHEDULER CERTIFICATION ===")
    print("Request reason:", report.request_reason)
    print("Requested step:", report.requested_step)

    print("\nSelected episodes:")
    for eid in report.selected_episode_ids:
        print(f"  ✓ {eid}")

    print("\nExcluded episodes:")
    for eid in report.excluded_episode_ids:
        reason = report.eligibility_reasons.get(eid, "unknown")
        print(f"  ✗ {eid} ({reason})")

    print("\nEligibility reasons:")
    for eid, reason in report.eligibility_reasons.items():
        print(f"  {eid}: {reason}")
