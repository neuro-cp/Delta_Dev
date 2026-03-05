from __future__ import annotations

from typing import List

from engine.sleep.orchestration.sleep_decision import SleepDecision
from engine.replay.requests.replay_request import ReplayRequest
from engine.replay.execution.replay_execution_config import ReplayExecutionConfig


class SleepToReplayAdapter:
    """
    Adapter translating a SleepDecision into replay-layer inputs.

    This adapter:
    - creates ReplayRequest objects
    - creates ReplayExecutionConfig objects
    - carries NO authority
    - performs NO execution
    """

    @staticmethod
    def build_replay_requests(
        *,
        decision: SleepDecision,
        current_step: int,
    ) -> List[ReplayRequest]:
        """
        Build replay requests corresponding to a sleep decision.
        """

        requests: List[ReplayRequest] = []

        for mode in decision.selected_replay_modes:
            requests.append(
                ReplayRequest(
                    reason=f"sleep:{decision.profile_name}",
                    requested_step=current_step,
                    urgency=None,
                )
            )

        return requests

    @staticmethod
    def build_execution_configs(
        *,
        decision: SleepDecision,
    ) -> List[ReplayExecutionConfig]:
        """
        Build execution configs corresponding to a sleep decision.
        """

        configs: List[ReplayExecutionConfig] = []

        for mode in decision.selected_replay_modes:
            configs.append(
                ReplayExecutionConfig(
                    mode=mode,
                )
            )

        return configs
