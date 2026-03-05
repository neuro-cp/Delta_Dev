from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget

from .execution_enablement_request import ExecutionEnablementRequest
from .execution_enablement_policy import ExecutionEnablementPolicy
from .execution_enablement_record import ExecutionEnablementRecord


class ExecutionEnablementController:
    """
    Sole authority allowed to modify ExecutionState
    by replacement (never mutation).
    """

    def __init__(self, state: ExecutionState):
        self._state = state
        self._remaining = 0

    @property
    def state(self) -> ExecutionState:
        return self._state

    def enable(self, request: ExecutionEnablementRequest) -> ExecutionEnablementRecord:
        if not ExecutionEnablementPolicy.is_valid(request):
            return ExecutionEnablementRecord(
                enabled=False,
                targets=set(),
                remaining_steps=0,
            )

        self._remaining = request.duration_steps

        self._state = ExecutionState(
            enabled=True,
            allowed_targets=set(request.targets),
        )

        return ExecutionEnablementRecord(
            enabled=True,
            targets=set(request.targets),
            remaining_steps=self._remaining,
        )

    def step(self) -> ExecutionEnablementRecord:
        if not self._state.enabled:
            return ExecutionEnablementRecord(False, set(), 0)

        self._remaining -= 1

        if self._remaining <= 0:
            self._state = ExecutionState(enabled=False, allowed_targets=None)
            return ExecutionEnablementRecord(False, set(), 0)

        return ExecutionEnablementRecord(
            True,
            set(self._state.allowed_targets or []),
            self._remaining,
        )
