from __future__ import annotations

"""
Certification test: REM replay determinism.

Verifies:
- Frame order is permuted
- Permutation is deterministic under fixed seed
"""

from engine.replay.execution.replay_executor import ReplayExecutor
from engine.replay.execution.replay_execution_config import ReplayExecutionConfig
from engine.replay.scheduling.replay_plan import ReplayPlan
from engine.replay.requests.replay_request import ReplayRequest
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class FakeEpisodeReplay:
    def replay_episode(self, episode_id: str):
        return [ObservationFrame(step=i) for i in range(10)]


class FakeHypothesisRunner:
    def __init__(self) -> None:
        self.frames = []

    def step(self, frame: ObservationFrame) -> None:
        self.frames.append(frame)

    def build_timeline(self):
        return {"frames": list(self.frames)}


def extract_steps(report):
    return [frame.step for frame in report.cognition_output["frames"]]


def test_rem_determinism() -> None:
    plan = ReplayPlan(
        request=ReplayRequest(reason="test"),
        selected_episode_ids=["ep_rem"],
        eligibility_reasons={"ep_rem": "eligible"},
    )

    exec_a = ReplayExecutor(
        episode_replay=FakeEpisodeReplay(),
        hypothesis_runner=FakeHypothesisRunner(),
        execution_config=ReplayExecutionConfig(mode="rem", seed=42),
    )

    exec_b = ReplayExecutor(
        episode_replay=FakeEpisodeReplay(),
        hypothesis_runner=FakeHypothesisRunner(),
        execution_config=ReplayExecutionConfig(mode="rem", seed=42),
    )

    report_a = exec_a.execute(plan)
    report_b = exec_b.execute(plan)

    steps_a = extract_steps(report_a)
    steps_b = extract_steps(report_b)

    assert steps_a == steps_b
    assert steps_a != list(range(10))  # must be permuted

    print("\n=== REM DETERMINISM ===")
    print("REM step order:", steps_a)
