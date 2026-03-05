from typing import Set

from engine.execution.execution_target import ExecutionTarget
from engine.execution.execution_record import ExecutionRecord
from .operator_execution_request import OperatorExecutionRequest
from .operator_execution_policy import OperatorExecutionPolicy


class OperatorExecutionAuthorization:
    """
    Authorizes operator execution requests and emits records only.
    """

    @staticmethod
    def authorize(
        request: OperatorExecutionRequest,
        *,
        allowed_targets: Set[ExecutionTarget],
    ) -> ExecutionRecord:
        permitted = OperatorExecutionPolicy.is_request_allowed(
            request,
            allowed_targets=allowed_targets,
        )

        return ExecutionRecord(
            target=None,              # governance-level, not a runtime target
            applied=permitted,
            value_snapshot=request,
        )
