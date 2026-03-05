from .execution_proposal import ExecutionProposal

class ExecutionProposalPolicy:
    @staticmethod
    def is_valid(proposal: ExecutionProposal) -> bool:
        if not proposal.suggested_targets:
            return False
        if not (0.0 <= proposal.confidence <= 1.0):
            return False
        return True
