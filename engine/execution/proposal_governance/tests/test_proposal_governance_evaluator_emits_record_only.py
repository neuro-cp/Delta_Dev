from engine.execution.proposal_governance.proposal_governance_request import ProposalGovernanceRequest
from engine.execution.proposal_governance.proposal_governance_evaluator import ProposalGovernanceEvaluator

def test_evaluator_emits_record_only():
    r = ProposalGovernanceRequest(proposal=object(), justification="ok")
    rec = ProposalGovernanceEvaluator.evaluate(r)
    assert rec.accepted is True
