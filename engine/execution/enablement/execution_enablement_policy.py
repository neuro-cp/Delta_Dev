from .execution_enablement_request import ExecutionEnablementRequest


class ExecutionEnablementPolicy:
    """
    Enforces time-bounded, scoped enablement.
    """

    @staticmethod
    def is_valid(request: ExecutionEnablementRequest) -> bool:
        if not request.targets:
            return False
        if request.duration_steps <= 0:
            return False
        return True
