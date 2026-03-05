from engine.execution.governance.operator_execution_request import (
    OperatorExecutionRequest
)


def test_operator_execution_request_is_pure_data():
    req = OperatorExecutionRequest(
        operator_id="alice",
        requested_targets=None,
        justification="test",
    )

    for value in req.__dict__.values():
        assert not callable(value)
