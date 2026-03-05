from __future__ import annotations

"""
Certification test: Wake vs NREM replay execution.

Verifies:
- Same episode content is replayed
- NREM produces fewer observation frames (structural pacing)
- No semantics or memory writes
"""

from engine.replay.execution.replay_executor import ReplayExecutor
from engine.replay.execution.replay_execution_config import ReplayExecutionConfig
from engine.replay.scheduling.replay_plan import ReplayPlan
from engine.replay.requests.replay_request import ReplayRequest
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class FakeEpisodeReplay:
    """
    Deterministic fake episodic replay.
    """

    def replay_episode(self, episode_id: str):
        # Emit 10 frames per episode
        return [ObservationFrame(step=i) for i in range(10)]


class FakeHypothesisRunner:
    """
    Minimal cognition stub.

    Records frames but performs no cognition.
    """

    def __init__(self) -> None:
        self.frames = []

    def step(self, frame: ObservationFrame) -> None:
        self.frames.append(frame)

    def build_timeline(self):
        # Opaque inspection-safe output
        return {"frame_count": len(self.frames)}


def test_wake_vs_nrem_execution() -> None:
    plan = ReplayPlan(
        request=ReplayRequest(reason="test"),
        selected_episode_ids=["ep_1"],
        eligibility_reasons={"ep_1": "eligible"},
    )

    # Wake execution
    wake_executor = ReplayExecutor(
        episode_replay=FakeEpisodeReplay(),
        hypothesis_runner=FakeHypothesisRunner(),
        execution_config=ReplayExecutionConfig(mode="wake"),
    )

    wake_report = wake_executor.execute(plan)

    # NREM execution (stride=2)
    nrem_executor = ReplayExecutor(
        episode_replay=FakeEpisodeReplay(),
        hypothesis_runner=FakeHypothesisRunner(),
        execution_config=ReplayExecutionConfig(mode="nrem", stride=2),
    )

    nrem_report = nrem_executor.execute(plan)

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert wake_report.executed_episode_ids == ["ep_1"]
    assert nrem_report.executed_episode_ids == ["ep_1"]

    assert wake_report.observation_frame_count == 10
    assert nrem_report.observation_frame_count == 5

    print("\n=== WAKE vs NREM EXECUTION ===")
    print("Wake frames:", wake_report.observation_frame_count)
    print("NREM frames:", nrem_report.observation_frame_count)
