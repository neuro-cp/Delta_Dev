from engine.execution.governance_enablement.governance_enablement_request import GovernanceEnablementRequest
from engine.execution.governance_enablement.governance_enablement_policy import GovernanceEnablementPolicy

def test_policy_rejects_invalid():
    r = GovernanceEnablementRequest(set(), 0, "")
    assert not GovernanceEnablementPolicy.is_valid(r)
