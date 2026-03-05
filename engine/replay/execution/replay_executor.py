from __future__ import annotations

from typing import List, Iterable, Protocol

from engine.replay.scheduling.replay_plan import ReplayPlan
from engine.replay.execution.replay_execution_report import ReplayExecutionReport
from engine.replay.execution.replay_execution_config import ReplayExecutionConfig

from engine.replay.modes.replay_mode import ReplayMode
from engine.replay.modes.wake_replay_mode import WakeReplayMode
from engine.replay.modes.nrem_replay_mode import NREMReplayMode
from engine.replay.modes.rem_replay_mode import REMReplayMode

from engine.cognition.hypothesis.offline.hypothesis_runner import HypothesisRunner
from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame


class EpisodeReplaySource(Protocol):
    """
    Minimal interface required for replay execution.

    Any object providing this method is a valid replay source.
    """

    def replay_episode(self, episode_id: str) -> Iterable[ObservationFrame]:
        ...


class ReplayExecutor:
    """
    Offline replay execution stub.

    This class bridges:
    ReplayPlan → Replay Source → Cognition

    It:
    - Executes replay strictly offline
    - Produces cognition outputs
    - Emits inspection artifacts

    It does NOT:
    - Modify runtime
    - Modify episodic memory
    - Persist cognition
    - Perform consolidation
    """

    def __init__(
        self,
        *,
        episode_replay: EpisodeReplaySource,
        hypothesis_runner: HypothesisRunner,
        execution_config: ReplayExecutionConfig | None = None,
    ) -> None:
        self._episode_replay = episode_replay
        self._hypothesis_runner = hypothesis_runner
        self._config = execution_config or ReplayExecutionConfig()

        self._mode = self._build_mode(self._config)

    def _build_mode(self, config: ReplayExecutionConfig) -> ReplayMode:
        """
        Instantiate the configured replay mode.
        """

        if config.mode == "wake":
            return WakeReplayMode()

        if config.mode == "nrem":
            return NREMReplayMode(
                stride=config.stride or 2,
            )

        if config.mode == "rem":
            return REMReplayMode(
                seed=config.seed,
            )

        raise ValueError(f"Unknown replay mode: {config.mode}")

    def execute(self, plan: ReplayPlan) -> ReplayExecutionReport:
        """
        Execute replay for the given ReplayPlan.

        Returns a ReplayExecutionReport describing what occurred.
        """

        executed_episodes: List[str] = []
        observation_frames: List[ObservationFrame] = []

        # --------------------------------------------------
        # Replay each selected episode (order preserved)
        # --------------------------------------------------
        for episode_id in plan.selected_episode_ids:
            raw_frames = self._episode_replay.replay_episode(episode_id)

            # Apply replay mode (execution style only)
            for frame in self._mode.iter_frames(raw_frames):
                self._hypothesis_runner.step(frame)
                observation_frames.append(frame)

            executed_episodes.append(episode_id)

        # --------------------------------------------------
        # Collect cognition outputs (inspection only)
        # --------------------------------------------------
        cognition_output = self._hypothesis_runner.build_timeline()

        return ReplayExecutionReport(
            replay_request_reason=plan.request.reason,
            executed_episode_ids=executed_episodes,
            cognition_output=cognition_output,
            observation_frame_count=len(observation_frames),
        )
