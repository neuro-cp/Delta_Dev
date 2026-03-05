from engine.execution.proposals.execution_proposal import ExecutionProposal
from engine.execution.execution_target import ExecutionTarget

def test_execution_proposal_is_pure_data():
    p = ExecutionProposal("learning", {ExecutionTarget.VALUE_BIAS}, 0.5)
    for v in p.__dict__.values():
        assert not callable(v)
