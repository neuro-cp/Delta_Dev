from engine.execution.execution_target import ExecutionTarget
from engine.execution.governance.operator_execution_request import (
    OperatorExecutionRequest
)
from engine.execution.governance.operator_execution_authorization import (
    OperatorExecutionAuthorization
)


def test_authorization_emits_record_only():
    req = OperatorExecutionRequest(
        operator_id="alice",
        requested_targets={ExecutionTarget.VALUE_BIAS},
        justification="test",
    )

    record = OperatorExecutionAuthorization.authorize(
        req,
        allowed_targets={ExecutionTarget.VALUE_BIAS},
    )

    assert record.applied is True
    assert record.value_snapshot is req
