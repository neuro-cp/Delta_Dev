from engine.execution.execution_gate import ExecutionGate
from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget


def test_execution_removal_is_noop():
    gate = ExecutionGate(ExecutionState(enabled=False))
    out = gate.apply(ExecutionTarget.ROUTING_GAIN, value=2.0, identity=1.0)
    assert out == 1.0
