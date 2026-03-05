from engine.execution.execution_gate import ExecutionGate
from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget


def test_execution_allows_allowed_adapter():
    gate = ExecutionGate(
        ExecutionState(enabled=True, allowed_targets={ExecutionTarget.VALUE_BIAS})
    )
    out = gate.apply(ExecutionTarget.VALUE_BIAS, value=0.8, identity=1.0)
    assert out == 0.8
    assert gate.records[0].applied is True
