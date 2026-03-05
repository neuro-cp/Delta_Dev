from .governance_enablement_request import GovernanceEnablementRequest
from .governance_enablement_policy import GovernanceEnablementPolicy
from .governance_enablement_record import GovernanceEnablementRecord

class GovernanceEnablementMapper:
    @staticmethod
    def map(request: GovernanceEnablementRequest) -> GovernanceEnablementRecord:
        if not GovernanceEnablementPolicy.is_valid(request):
            return GovernanceEnablementRecord(False, request, "invalid_request")
        return GovernanceEnablementRecord(True, request, "structurally_valid")
