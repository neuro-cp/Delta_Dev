from typing import Optional, Set

from engine.execution.execution_target import ExecutionTarget
from .operator_execution_request import OperatorExecutionRequest


class OperatorExecutionPolicy:
    """
    Declarative governance policy defining what operators may request.
    """

    @staticmethod
    def is_request_allowed(
        request: OperatorExecutionRequest,
        *,
        allowed_targets: Set[ExecutionTarget],
    ) -> bool:
        if request.requested_targets is None:
            return False

        return request.requested_targets.issubset(allowed_targets)
