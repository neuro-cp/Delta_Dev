from __future__ import annotations

"""
Certification test: sleep cycle determinism.

Invariant:
Given the same SleepDecision, episode metadata, and replay infrastructure,
SleepCycle must produce identical replay execution structure.

This test guards against:
- accidental randomness
- wiring drift
- adapter regressions
"""

from engine.sleep.orchestration.sleep_decision import SleepDecision
from engine.sleep.orchestration.sleep_cycle import SleepCycle

from engine.replay.execution.replay_execution_report import ReplayExecutionReport
from engine.replay.requests.replay_request import ReplayRequest


# --------------------------------------------------
# Fakes / deterministic stubs
# --------------------------------------------------

class DeterministicReplayScheduler:
    """
    Always returns the same plan regardless of input.
    """

    def schedule(self, *, request: ReplayRequest, episodes_meta: dict):
        from engine.replay.scheduling.replay_plan import ReplayPlan

        return ReplayPlan(
            request=request,
            selected_episode_ids=["ep_A", "ep_B"],
            eligibility_reasons={
                "ep_A": "eligible",
                "ep_B": "eligible",
            },
        )


class DeterministicReplayExecutor:
    """
    Always returns the same execution report for a given plan.
    """

    def execute(self, plan):
        return ReplayExecutionReport(
            replay_request_reason=plan.request.reason,
            executed_episode_ids=list(plan.selected_episode_ids),
            cognition_output={"deterministic": True},
            observation_frame_count=99,
            sleep_profile=None,
            origin=plan.request.origin,
        )


# --------------------------------------------------
# Test
# --------------------------------------------------

def test_sleep_cycle_is_deterministic() -> None:
    decision = SleepDecision(
        profile_name="nrem_heavy",
        selected_replay_modes=["nrem"],
        episode_budget=2,
        justification="determinism_test",
    )

    episodes_meta = {
        "ep_A": {"length": 10},
        "ep_B": {"length": 12},
    }

    scheduler = DeterministicReplayScheduler()
    executor = DeterministicReplayExecutor()

    cycle = SleepCycle(
        replay_scheduler=scheduler,
        replay_executor=executor,
    )

    # --------------------------------------------------
    # Run sleep cycle twice
    # --------------------------------------------------
    reports_run_1 = cycle.run(
        decision=decision,
        episodes_meta=episodes_meta,
        current_step=500,
    )

    reports_run_2 = cycle.run(
        decision=decision,
        episodes_meta=episodes_meta,
        current_step=500,
    )

    # --------------------------------------------------
    # Assertions: structural determinism
    # --------------------------------------------------
    assert len(reports_run_1) == len(reports_run_2) == 1

    r1 = reports_run_1[0]
    r2 = reports_run_2[0]

    assert r1.replay_request_reason == r2.replay_request_reason
    assert r1.executed_episode_ids == r2.executed_episode_ids
    assert r1.observation_frame_count == r2.observation_frame_count

    print("\n=== SLEEP CYCLE DETERMINISM ===")
    print("Episodes:", r1.executed_episode_ids)
    print("Frames:", r1.observation_frame_count)
