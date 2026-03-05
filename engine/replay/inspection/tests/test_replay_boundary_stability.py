from engine.replay.requests.replay_request import ReplayRequest
from engine.replay.scheduling.replay_scheduler import ReplayScheduler
from engine.replay.execution.replay_executor import ReplayExecutor
from engine.replay.execution.replay_execution_config import ReplayExecutionConfig

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook

from engine.replay.inspection.replay_boundary_report import (
    build_replay_boundary_report,
)


class FakeReplaySource:
    def __init__(self, frames):
        self._frames = frames

    def replay_episode(self, episode_id):
        return self._frames


class FakeHypothesisRunner:
    def step(self, frame):
        pass

    def build_timeline(self):
        return []


def test_replay_boundary_stability_across_modes():
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    hook = EpisodeRuntimeHook(tracker=tracker)

    # Build episodes
    hook.step(step=0, boundary_events=[])
    hook.step(step=1, boundary_events=[])
    hook.step(step=2, boundary_events=[])
    hook.step(step=3, boundary_events=[])
    hook.step(step=4, boundary_events=[])

    hook.step(step=5, boundary_events=[
        type("E", (), {"step": 5, "reason": "test"})()
    ])

    # Episode metadata for scheduler
    episodes_meta = {
        str(ep.episode_id): {
            "length": ep.duration_steps or 5,
            "decision_count": ep.decision_count,
            "end_step": ep.end_step or 5,
        }
        for ep in tracker.episodes
    }

    scheduler = ReplayScheduler(max_episodes=5)
    request = ReplayRequest(reason="test")
    plan = scheduler.schedule(request, episodes_meta)

    fake_frames = [object(), object(), object()]

    reports = []
    for mode in ("wake", "nrem", "rem"):
        executor = ReplayExecutor(
            episode_replay=FakeReplaySource(fake_frames),
            hypothesis_runner=FakeHypothesisRunner(),
            execution_config=ReplayExecutionConfig(mode=mode, seed=42),
        )

        execution_report = executor.execute(plan)

        boundary_report = build_replay_boundary_report(
            execution_report=execution_report,
            episode_trace=trace,
        )

        reports.append(boundary_report)

    assert reports[0] == reports[1] == reports[2]
