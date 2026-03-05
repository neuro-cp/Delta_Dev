from engine.execution.proposals.execution_proposal import ExecutionProposal
from engine.execution.proposals.execution_proposal_policy import ExecutionProposalPolicy

def test_policy_rejects_empty_targets():
    p = ExecutionProposal("learning", set(), 0.5)
    assert not ExecutionProposalPolicy.is_valid(p)
