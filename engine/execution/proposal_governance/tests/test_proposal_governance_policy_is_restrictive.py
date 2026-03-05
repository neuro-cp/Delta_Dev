from engine.execution.proposal_governance.proposal_governance_request import ProposalGovernanceRequest
from engine.execution.proposal_governance.proposal_governance_policy import ProposalGovernancePolicy

def test_policy_rejects_empty_justification():
    r = ProposalGovernanceRequest(proposal=object(), justification="")
    assert not ProposalGovernancePolicy.is_valid(r)
