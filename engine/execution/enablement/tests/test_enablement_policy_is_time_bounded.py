from engine.execution.enablement.execution_enablement_policy import (
    ExecutionEnablementPolicy
)
from engine.execution.enablement.execution_enablement_request import (
    ExecutionEnablementRequest
)


def test_policy_rejects_zero_duration():
    req = ExecutionEnablementRequest(set(), 0)
    assert not ExecutionEnablementPolicy.is_valid(req)
