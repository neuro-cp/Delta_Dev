from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget
from engine.execution.enablement.execution_enablement_controller import (
    ExecutionEnablementController
)
from engine.execution.enablement.execution_enablement_request import (
    ExecutionEnablementRequest
)


def test_enablement_applies_and_expires():
    state = ExecutionState(enabled=False)
    ctrl = ExecutionEnablementController(state)

    req = ExecutionEnablementRequest(
        targets={ExecutionTarget.VALUE_BIAS},
        duration_steps=2,
    )

    ctrl.enable(req)
    assert ctrl.state.enabled is True

    ctrl.step()
    ctrl.step()

    assert ctrl.state.enabled is False
