from engine.execution.enablement.execution_enablement_request import (
    ExecutionEnablementRequest
)


def test_enablement_request_is_pure_data():
    req = ExecutionEnablementRequest(set(), 1)
    for v in req.__dict__.values():
        assert not callable(v)
