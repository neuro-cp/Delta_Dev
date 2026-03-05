from engine.execution.execution_state import ExecutionState
from engine.execution.enablement.execution_enablement_controller import ExecutionEnablementController
from engine.execution.governance_enablement.governance_enablement_record import GovernanceEnablementRecord
from engine.execution.governance_execution.governance_execution_adapter import GovernanceExecutionAdapter

def test_adapter_noop_on_reject():
    state = ExecutionState(enabled=False)
    controller = ExecutionEnablementController(state)

    record = GovernanceEnablementRecord(
        accepted=False,
        request_snapshot=None,
        reason="reject",
    )

    GovernanceExecutionAdapter.apply(record, controller)

    assert controller.state.enabled is False
