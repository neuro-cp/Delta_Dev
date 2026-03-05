from engine.execution.execution_target import ExecutionTarget
from engine.execution.governance_enablement.governance_enablement_request import GovernanceEnablementRequest
from engine.execution.governance_enablement.governance_enablement_mapper import GovernanceEnablementMapper

def test_mapper_emits_record_only():
    r = GovernanceEnablementRequest({ExecutionTarget.VALUE_BIAS}, 1, "ok")
    rec = GovernanceEnablementMapper.map(r)
    assert rec.accepted is True
