from engine.execution.execution_gate import ExecutionGate
from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget


def test_execution_off_is_identity():
    gate = ExecutionGate(ExecutionState(enabled=False))
    out = gate.apply(ExecutionTarget.VALUE_BIAS, value=0.9, identity=1.0)
    assert out == 1.0
    assert gate.records[0].applied is False
