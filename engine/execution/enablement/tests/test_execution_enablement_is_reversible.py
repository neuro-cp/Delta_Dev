from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget
from engine.execution.enablement.execution_enablement_controller import (
    ExecutionEnablementController
)
from engine.execution.enablement.execution_enablement_request import (
    ExecutionEnablementRequest
)


def test_enablement_reversibility():
    state = ExecutionState(enabled=False)
    ctrl = ExecutionEnablementController(state)

    req = ExecutionEnablementRequest(
        targets={ExecutionTarget.PFC_CONTEXT_GAIN},
        duration_steps=1,
    )

    ctrl.enable(req)
    ctrl.step()

    assert state.enabled is False
