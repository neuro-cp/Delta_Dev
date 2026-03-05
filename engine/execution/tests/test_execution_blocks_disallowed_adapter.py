from engine.execution.execution_gate import ExecutionGate
from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget


def test_execution_blocks_disallowed_adapter():
    gate = ExecutionGate(
        ExecutionState(enabled=True, allowed_targets=set())
    )
    out = gate.apply(ExecutionTarget.VALUE_BIAS, value=0.5, identity=1.0)
    assert out == 1.0
    assert gate.records[0].applied is False
