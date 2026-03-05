from .proposal_governance_request import ProposalGovernanceRequest

class ProposalGovernancePolicy:
    @staticmethod
    def is_valid(request: ProposalGovernanceRequest) -> bool:
        return bool(request.justification)
