from typing import Any, Optional, List

from .execution_state import ExecutionState
from .execution_target import ExecutionTarget
from .execution_policy import ExecutionPolicy
from .execution_record import ExecutionRecord


class ExecutionGate:
    def __init__(self, state: ExecutionState):
        self._state = state
        self._records: List[ExecutionRecord] = []

    @property
    def records(self):
        return tuple(self._records)

    def apply(self, target: ExecutionTarget, value: Any, identity: Any) -> Any:
        if not self._state.is_allowed(target):
            self._records.append(
                ExecutionRecord(target=target, applied=False, value_snapshot=identity)
            )
            return identity

        if not ExecutionPolicy.is_permitted(target):
            self._records.append(
                ExecutionRecord(target=target, applied=False, value_snapshot=identity)
            )
            return identity

        self._records.append(
            ExecutionRecord(target=target, applied=True, value_snapshot=value)
        )
        return value
