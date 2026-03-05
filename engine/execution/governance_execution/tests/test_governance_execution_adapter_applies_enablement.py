from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget
from engine.execution.enablement.execution_enablement_controller import ExecutionEnablementController
from engine.execution.governance_enablement.governance_enablement_record import GovernanceEnablementRecord
from engine.execution.governance_execution.governance_execution_adapter import GovernanceExecutionAdapter

class DummyRequest:
    def __init__(self):
        self.targets = {ExecutionTarget.VALUE_BIAS}
        self.duration_steps = 1

def test_adapter_applies_enablement():
    state = ExecutionState(enabled=False)
    controller = ExecutionEnablementController(state)

    record = GovernanceEnablementRecord(
        accepted=True,
        request_snapshot=DummyRequest(),
        reason="ok",
    )

    GovernanceExecutionAdapter.apply(record, controller)

    assert controller.state.enabled is True
