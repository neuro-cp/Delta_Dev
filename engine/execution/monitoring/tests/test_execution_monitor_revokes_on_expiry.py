from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget
from engine.execution.enablement.execution_enablement_controller import ExecutionEnablementController
from engine.execution.enablement.execution_enablement_request import ExecutionEnablementRequest
from engine.execution.monitoring.execution_monitor import ExecutionMonitor

def test_monitor_revokes_on_expiry():
    state = ExecutionState(enabled=False)
    ctrl = ExecutionEnablementController(state)

    ctrl.enable(ExecutionEnablementRequest({ExecutionTarget.VALUE_BIAS}, 1))
    monitor = ExecutionMonitor(ctrl)

    monitor.step()
    assert ctrl.state.enabled is False
