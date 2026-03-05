from engine.execution.execution_target import ExecutionTarget
from engine.execution.proposals.execution_proposal import ExecutionProposal
from engine.execution.proposals.execution_proposal_evaluator import ExecutionProposalEvaluator

def test_evaluator_emits_record_only():
    p = ExecutionProposal("learning", {ExecutionTarget.VALUE_BIAS}, 0.8)
    record = ExecutionProposalEvaluator.evaluate(p)
    assert record.accepted is True
