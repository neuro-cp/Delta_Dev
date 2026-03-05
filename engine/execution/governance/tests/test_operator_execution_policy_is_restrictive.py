from engine.execution.execution_target import ExecutionTarget
from engine.execution.governance.operator_execution_request import (
    OperatorExecutionRequest
)
from engine.execution.governance.operator_execution_policy import (
    OperatorExecutionPolicy
)


def test_operator_execution_policy_blocks_unlisted_targets():
    req = OperatorExecutionRequest(
        operator_id="alice",
        requested_targets={ExecutionTarget.VALUE_BIAS},
        justification="test",
    )

    allowed = {ExecutionTarget.PFC_CONTEXT_GAIN}

    assert not OperatorExecutionPolicy.is_request_allowed(
        req,
        allowed_targets=allowed,
    )
