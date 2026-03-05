from .governance_enablement_request import GovernanceEnablementRequest

class GovernanceEnablementPolicy:
    @staticmethod
    def is_valid(request: GovernanceEnablementRequest) -> bool:
        if not request.targets:
            return False
        if request.duration_steps <= 0:
            return False
        if not request.rationale:
            return False
        return True
