from engine.execution.governance_enablement.governance_enablement_request import GovernanceEnablementRequest
from engine.execution.execution_target import ExecutionTarget

def test_request_is_pure_data():
    r = GovernanceEnablementRequest({ExecutionTarget.VALUE_BIAS}, 1, "ok")
    for v in r.__dict__.values():
        assert not callable(v)
