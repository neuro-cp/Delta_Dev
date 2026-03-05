from __future__ import annotations

from typing import List

from engine.sleep.orchestration.sleep_decision import SleepDecision
from engine.sleep.orchestration.sleep_to_replay_adapter import SleepToReplayAdapter

from engine.replay.scheduling.replay_scheduler import ReplayScheduler
from engine.replay.execution.replay_executor import ReplayExecutor
from engine.replay.execution.replay_execution_report import ReplayExecutionReport


class SleepCycle:
    """
    Offline sleep cycle runner.

    This class:
    - wires sleep orchestration to replay
    - executes replay strictly offline
    - produces replay execution reports

    It does NOT:
    - modify runtime
    - modify episodic memory
    - influence cognition directly
    """

    def __init__(
        self,
        *,
        replay_scheduler: ReplayScheduler,
        replay_executor: ReplayExecutor,
    ) -> None:
        self._replay_scheduler = replay_scheduler
        self._replay_executor = replay_executor

    def run(
        self,
        *,
        decision: SleepDecision,
        episodes_meta: dict,
        current_step: int,
    ) -> List[ReplayExecutionReport]:
        """
        Execute a full offline sleep cycle.
        """

        reports: List[ReplayExecutionReport] = []

        # --------------------------------------------------
        # Translate sleep decision → replay inputs
        # --------------------------------------------------
        replay_requests = SleepToReplayAdapter.build_replay_requests(
            decision=decision,
            current_step=current_step,
        )

        execution_configs = SleepToReplayAdapter.build_execution_configs(
            decision=decision,
        )

        # --------------------------------------------------
        # Schedule + execute replay for each mode
        # --------------------------------------------------
        for request, config in zip(replay_requests, execution_configs):
            plan = self._replay_scheduler.schedule(
                request=request,
                episodes_meta=episodes_meta,
            )

            # Executor already holds its config
            report = self._replay_executor.execute(plan)
            reports.append(report)

        return reports
