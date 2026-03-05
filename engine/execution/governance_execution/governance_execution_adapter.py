from engine.execution.governance_enablement.governance_enablement_record import GovernanceEnablementRecord
from engine.execution.enablement.execution_enablement_request import ExecutionEnablementRequest
from engine.execution.enablement.execution_enablement_controller import ExecutionEnablementController

class GovernanceExecutionAdapter:
    @staticmethod
    def apply(record: GovernanceEnablementRecord, controller: ExecutionEnablementController):
        if not record.accepted:
            return None

        request = ExecutionEnablementRequest(
            targets=record.request_snapshot.targets,
            duration_steps=record.request_snapshot.duration_steps,
        )

        return controller.enable(request)
