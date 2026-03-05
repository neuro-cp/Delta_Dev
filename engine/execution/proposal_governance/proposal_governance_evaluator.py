from .proposal_governance_request import ProposalGovernanceRequest
from .proposal_governance_policy import ProposalGovernancePolicy
from .proposal_governance_record import ProposalGovernanceRecord

class ProposalGovernanceEvaluator:
    @staticmethod
    def evaluate(request: ProposalGovernanceRequest) -> ProposalGovernanceRecord:
        if not ProposalGovernancePolicy.is_valid(request):
            return ProposalGovernanceRecord(False, request, "invalid_request")
        return ProposalGovernanceRecord(True, request, "structurally_valid")
