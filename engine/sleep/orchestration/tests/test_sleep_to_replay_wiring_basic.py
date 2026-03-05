from __future__ import annotations

"""
Certification test: sleep → replay wiring (basic).

Verifies:
- SleepDecision is translated into replay requests
- ReplayScheduler is invoked
- ReplayExecutor is invoked
- Metadata (origin, sleep_profile) propagates
- No runtime or cognition semantics are involved
"""

from engine.sleep.orchestration.sleep_decision import SleepDecision
from engine.sleep.orchestration.sleep_cycle import SleepCycle
from engine.sleep.orchestration.sleep_to_replay_adapter import SleepToReplayAdapter

from engine.replay.scheduling.replay_scheduler import ReplayScheduler
from engine.replay.execution.replay_executor import ReplayExecutor
from engine.replay.execution.replay_execution_report import ReplayExecutionReport

from engine.replay.requests.replay_request import ReplayRequest
from engine.replay.execution.replay_execution_config import ReplayExecutionConfig


# --------------------------------------------------
# Fakes / stubs
# --------------------------------------------------

class FakeReplayScheduler:
    """
    Minimal scheduler stub: always selects the same episodes.
    """

    def schedule(self, *, request: ReplayRequest, episodes_meta: dict):
        from engine.replay.scheduling.replay_plan import ReplayPlan

        return ReplayPlan(
            request=request,
            selected_episode_ids=["ep_1", "ep_2"],
            eligibility_reasons={
                "ep_1": "eligible",
                "ep_2": "eligible",
            },
        )


class FakeReplayExecutor:
    """
    Minimal executor stub: returns a deterministic report.
    """

    def execute(self, plan):
        return ReplayExecutionReport(
            replay_request_reason=plan.request.reason,
            executed_episode_ids=plan.selected_episode_ids,
            cognition_output={"fake": True},
            observation_frame_count=42,
            sleep_profile=None,
            origin=plan.request.origin,
        )


# --------------------------------------------------
# Test
# --------------------------------------------------

def test_sleep_to_replay_wiring_basic() -> None:
    # --------------------------------------------------
    # Sleep decision (policy output)
    # --------------------------------------------------
    decision = SleepDecision(
        profile_name="nrem_heavy",
        selected_replay_modes=["nrem"],
        episode_budget=3,
        justification="test",
    )

    # --------------------------------------------------
    # Fake replay infra
    # --------------------------------------------------
    scheduler = FakeReplayScheduler()
    executor = FakeReplayExecutor()

    cycle = SleepCycle(
        replay_scheduler=scheduler,
        replay_executor=executor,
    )

    # --------------------------------------------------
    # Episodes metadata (scheduler input)
    # --------------------------------------------------
    episodes_meta = {
        "ep_1": {"length": 10},
        "ep_2": {"length": 12},
    }

    # --------------------------------------------------
    # Run sleep cycle
    # --------------------------------------------------
    reports = cycle.run(
        decision=decision,
        episodes_meta=episodes_meta,
        current_step=100,
    )

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert len(reports) == 1

    report = reports[0]

    assert report.executed_episode_ids == ["ep_1", "ep_2"]
    assert report.observation_frame_count == 42
    assert report.replay_request_reason == "sleep:nrem_heavy"

    print("\n=== SLEEP → REPLAY WIRING ===")
    print("Executed episodes:", report.executed_episode_ids)
    print("Replay reason:", report.replay_request_reason)
