from engine.execution.proposal_governance.proposal_governance_request import ProposalGovernanceRequest

def test_request_is_pure_data():
    r = ProposalGovernanceRequest(proposal=object(), justification="ok")
    for v in r.__dict__.values():
        assert not callable(v)
