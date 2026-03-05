from typing import Set

from .execution_target import ExecutionTarget


class ExecutionPolicy:
    ALLOWED: Set[ExecutionTarget] = {
        ExecutionTarget.VALUE_BIAS,
        ExecutionTarget.URGENCY_RELIEF,
        ExecutionTarget.SALIENCE_GAIN,
        ExecutionTarget.ROUTING_GAIN,
        ExecutionTarget.PFC_CONTEXT_GAIN,
        ExecutionTarget.DECISION_FX_GAIN,
        ExecutionTarget.DECISION_BIAS,
    }

    @classmethod
    def is_permitted(cls, target: ExecutionTarget) -> bool:
        return target in cls.ALLOWED
