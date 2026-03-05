from .execution_proposal import ExecutionProposal
from .execution_proposal_policy import ExecutionProposalPolicy
from .execution_proposal_record import ExecutionProposalRecord

class ExecutionProposalEvaluator:
    @staticmethod
    def evaluate(proposal: ExecutionProposal) -> ExecutionProposalRecord:
        if not ExecutionProposalPolicy.is_valid(proposal):
            return ExecutionProposalRecord(False, proposal, "invalid_proposal")
        return ExecutionProposalRecord(True, proposal, "structurally_valid")
